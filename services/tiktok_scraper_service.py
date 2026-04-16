import json
import re
from typing import List, Dict, Optional, Tuple

import agentql
import pandas as pd
from playwright.sync_api import sync_playwright


QUERY = """
{
    comments[] {
        text
        author
    }
}
"""


class TikTokScraperService:
    def __init__(
        self,
        user_data_dir: str = "./playwright_profile",
        channel: str = "chrome",
        headless: bool = False,
    ):
        self.user_data_dir = user_data_dir
        self.channel = channel
        self.headless = headless

    @staticmethod
    def pause_video(page):
        page.evaluate("""
        () => {
            const videos = document.querySelectorAll('video');
            videos.forEach(v => {
                v.pause();
                v.muted = true;
            });
        }
        """)

    @staticmethod
    def normalize_comment(comment: Dict) -> Dict:
        text = (comment.get("text") or "").strip()
        author = (comment.get("author") or "").strip()
        return {
            "text": text,
            "author": author,
        }

    @staticmethod
    def is_valid_comment(comment: Dict) -> bool:
        return bool(comment["text"]) and bool(comment["author"])

    @staticmethod
    def comment_key(comment: Dict) -> str:
        return f'{comment["author"]}||{comment["text"]}'

    @staticmethod
    def comments_to_dataframe(
        comments: List[Dict],
        comment_column: str = "comment_text"
    ) -> pd.DataFrame:
        if not comments:
            return pd.DataFrame(columns=[comment_column, "author"])

        df = pd.DataFrame(comments)
        df = df.rename(columns={"text": comment_column})
        return df[[comment_column, "author"]]

    @staticmethod
    def parse_count_text(raw_text: str) -> Optional[int]:
        """
        Converts TikTok-style count text to int.
        Examples:
        - '167' -> 167
        - '1,234' -> 1234
        - '1.2K' -> 1200
        - '2,5K' -> 2500
        - '3M' -> 3000000
        """
        if not raw_text:
            return None

        text = raw_text.strip().upper().replace(" ", "")
        text = text.replace("\u00A0", "")

        # Keep digits, comma, dot, K, M
        text = re.sub(r"[^0-9K M\.,]", "", text).replace(" ", "")
        if not text:
            return None

        try:
            if text.endswith("K"):
                number = text[:-1].replace(",", ".")
                return int(float(number) * 1_000)

            if text.endswith("M"):
                number = text[:-1].replace(",", ".")
                return int(float(number) * 1_000_000)

            # Plain integer with separators
            plain = text.replace(".", "").replace(",", "")
            return int(plain)
        except Exception:
            return None

    def extract_comment_count(self, page) -> Optional[int]:
        """
        Tries multiple selectors / DOM fallbacks to get TikTok's official comment count.
        """
        selectors = [
            'strong[data-e2e="comment-count"]',
            '[data-e2e="comment-count"]',
            'strong[data-e2e="browse-comment-count"]',
            '[data-e2e="browse-comment-count"]',
        ]

        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if locator.count() > 0:
                    raw_text = (locator.inner_text(timeout=2000) or "").strip()
                    parsed = self.parse_count_text(raw_text)
                    if parsed is not None:
                        print(f"[comment_count] Fundet via selector '{selector}': {raw_text} -> {parsed}")
                        return parsed
            except Exception:
                pass

        try:
            raw_text = page.evaluate("""
            () => {
                const candidates = [...document.querySelectorAll('strong, span, div')];
                for (const el of candidates) {
                    const dataE2E = (el.getAttribute('data-e2e') || '').toLowerCase();
                    const text = (el.innerText || '').trim();

                    if (dataE2E.includes('comment-count') && text) {
                        return text;
                    }
                }
                return null;
            }
            """)
            parsed = self.parse_count_text(raw_text or "")
            if parsed is not None:
                print(f"[comment_count] Fundet via DOM fallback: {raw_text} -> {parsed}")
                return parsed
        except Exception:
            pass

        print("[comment_count] Kunne ikke finde comment count.")
        return None

    def handle_cookie_popup(self, page):
        possible_buttons = [
            "button:has-text('Accept all')",
            "button:has-text('Accept')",
            "button:has-text('Allow all')",
            "button:has-text('Tillad alle')",
            "button:has-text('Accepter alle')",
        ]

        for selector in possible_buttons:
            try:
                button = page.locator(selector).first
                if button.is_visible(timeout=1500):
                    button.click()
                    page.wait_for_timeout(1000)
                    return
            except Exception:
                pass

    def open_comment_panel(self, page):
        possible_selectors = [
            "[data-e2e='comment-icon']",
            "[data-e2e='browse-comment-icon']",
            "button[aria-label*='comment' i]",
            "button[aria-label*='kommentar' i]",
            "div[role='button'][aria-label*='comment' i]",
            "div[role='button'][aria-label*='kommentar' i]",
            "span:has-text('comments')",
            "span:has-text('kommentarer')",
        ]

        for selector in possible_selectors:
            try:
                locator = page.locator(selector).first
                locator.wait_for(timeout=3000)
                locator.click()
                page.wait_for_timeout(2500)
                return True
            except Exception:
                pass

        try:
            clicked = page.evaluate("""
            () => {
                const elements = [...document.querySelectorAll('button, div[role="button"], span')];
                const candidate = elements.find(el => {
                    const text = (el.innerText || '').toLowerCase();
                    const aria = (el.getAttribute('aria-label') || '').toLowerCase();
                    return text.includes('comment') ||
                           text.includes('kommentar') ||
                           aria.includes('comment') ||
                           aria.includes('kommentar');
                });

                if (candidate) {
                    candidate.click();
                    return true;
                }
                return false;
            }
            """)
            if clicked:
                page.wait_for_timeout(2500)
                return True
        except Exception:
            pass

        return False

    def find_comment_scroll_container(self, page):
        try:
            result = page.evaluate("""
                () => {
                    const commentSelectors = [
                        "[data-e2e='comment-level-1']",
                        "[data-e2e='comment-item']",
                        "[data-e2e*='comment-level']",
                        "[data-e2e*='comment-username']",
                        "div[class*='CommentItem']",
                        "div[class*='DivCommentItemContainer']"
                    ];

                    function isScrollable(node) {
                        if (!node || node.nodeType !== 1) return false;
                        const style = window.getComputedStyle(node);
                        const overflowY = style.overflowY;
                        return (
                            (overflowY === 'auto' || overflowY === 'scroll' || overflowY === 'overlay') &&
                            node.scrollHeight > node.clientHeight
                        );
                    }

                    for (const selector of commentSelectors) {
                        const items = document.querySelectorAll(selector);
                        if (!items.length) continue;

                        for (const item of items) {
                            let current = item.parentElement;
                            while (current) {
                                if (isScrollable(current)) {
                                    return {
                                        found: true,
                                        selectorUsed: selector,
                                        tagName: current.tagName,
                                        className: current.className || "",
                                        dataE2E: current.getAttribute("data-e2e") || "",
                                        scrollTop: current.scrollTop || 0,
                                        scrollHeight: current.scrollHeight || 0,
                                        clientHeight: current.clientHeight || 0,
                                        overflowY: window.getComputedStyle(current).overflowY || ""
                                    };
                                }
                                current = current.parentElement;
                            }
                        }
                    }

                    return { found: false };
                }
            """)

            print(f"[find_container] Resultat: {result}")
            return result

        except Exception as e:
            print(f"[find_container] Fejl: {e}")
            return {"found": False, "error": str(e)}

    def extract_visible_comments_from_dom(self, page) -> List[Dict]:
        selectors = [
            "[data-e2e='comment-level-1']",
            "div[class*='CommentItem']",
            "div[class*='DivCommentItemContainer']",
        ]

        all_comments = []
        seen = set()

        for selector in selectors:
            try:
                items = page.locator(selector)
                count = items.count()

                if count == 0:
                    continue

                print(f"[extract] Bruger selector '{selector}' med {count} items")

                for i in range(count):
                    item = items.nth(i)

                    try:
                        if not item.is_visible(timeout=500):
                            continue
                    except Exception:
                        continue

                    try:
                        text = ""
                        author = ""

                        author_selectors = [
                            "[data-e2e*='comment-username']",
                            "span[class*='UserName']",
                            "a[href*='@']",
                        ]
                        for a_sel in author_selectors:
                            try:
                                a_loc = item.locator(a_sel).first
                                if a_loc.count() > 0:
                                    author = (a_loc.inner_text(timeout=500) or "").strip()
                                    if author:
                                        break
                            except Exception:
                                pass

                        text_selectors = [
                            "[data-e2e='comment-level-1'] span",
                            "p",
                            "span",
                        ]
                        for t_sel in text_selectors:
                            try:
                                text_nodes = item.locator(t_sel)
                                node_count = text_nodes.count()
                                collected = []

                                for j in range(min(node_count, 10)):
                                    try:
                                        val = (text_nodes.nth(j).inner_text(timeout=300) or "").strip()
                                        if val:
                                            collected.append(val)
                                    except Exception:
                                        pass

                                if collected:
                                    text = " ".join(collected).strip()
                                    break
                            except Exception:
                                pass

                        text = " ".join(text.split())
                        author = " ".join(author.split())

                        if not text or not author:
                            continue

                        key = f"{author}||{text}"
                        if key in seen:
                            continue

                        seen.add(key)
                        all_comments.append({
                            "author": author,
                            "text": text,
                        })

                    except Exception:
                        continue

            except Exception as e:
                print(f"[extract] Fejl ved selector '{selector}': {e}")

        return all_comments

    def scroll_comment_panel(
        self,
        page,
        scroll_rounds: int = 3,
        pause_ms: int = 1500,
    ) -> bool:
        comment_selectors = [
            "[data-e2e='comment-level-1']",
            "div[class*='CommentItem']",
            "div[class*='DivCommentItemContainer']",
        ]

        for round_no in range(1, scroll_rounds + 1):
            try:
                target_box = None
                used_selector = None

                for selector in comment_selectors:
                    items = page.locator(selector)
                    count = items.count()

                    if count == 0:
                        continue

                    for i in range(count - 1, -1, -1):
                        item = items.nth(i)
                        try:
                            if not item.is_visible(timeout=300):
                                continue
                            box = item.bounding_box()
                            if box:
                                target_box = box
                                used_selector = selector
                                break
                        except Exception:
                            continue

                    if target_box:
                        break

                if not target_box:
                    print(f"[scroll] Runde {round_no}: ingen synlig comment-boks fundet, fallback til page wheel.")
                    page.mouse.wheel(0, 2000)
                    page.wait_for_timeout(pause_ms)
                    continue

                x = target_box["x"] + min(50, target_box["width"] / 2)
                y = target_box["y"] + min(30, target_box["height"] / 2)

                print(
                    f"[scroll] Runde {round_no}: bruger selector='{used_selector}', "
                    f"x={x:.1f}, y={y:.1f}"
                )

                page.mouse.move(x, y)
                page.mouse.wheel(0, 2200)
                page.wait_for_timeout(pause_ms)

                try:
                    page.keyboard.press("PageDown")
                    page.wait_for_timeout(400)
                except Exception:
                    pass

                try:
                    page.wait_for_page_ready_state()
                except Exception:
                    pass

            except Exception as e:
                print(f"[scroll] Fejl i runde {round_no}: {e}")
                return False

        return True

    def scrape_comments(
        self,
        video_url: str,
        max_scroll_iterations: int = 40,
        stable_rounds_required: int = 4,
        wait_after_load_ms: int = 5000,
        wait_between_rounds_ms: int = 1500,
    ) -> Tuple[List[Dict], Optional[int]]:
        all_comments = {}

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                channel=self.channel,
                headless=self.headless,
                no_viewport=True,
            )

            page = browser.new_page()

            try:
                print(f"\n[SCRAPE] Åbner video: {video_url}")
                page.goto(video_url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(wait_after_load_ms)

                self.handle_cookie_popup(page)
                self.pause_video(page)

                comment_count = self.extract_comment_count(page)

                panel_opened = self.open_comment_panel(page)
                if not panel_opened:
                    raise RuntimeError("Kunne ikke åbne TikTok kommentarpanelet automatisk.")

                print("[SCRAPE] Kommentarpanel åbnet.")
                page.wait_for_timeout(3000)

                stable_rounds = 0
                previous_unique_count = 0

                self.scroll_comment_panel(page, scroll_rounds=4, pause_ms=1200)

                for iteration in range(1, max_scroll_iterations + 1):
                    print(f"\n========== ITERATION {iteration}/{max_scroll_iterations} ==========")

                    page.wait_for_timeout(wait_between_rounds_ms)

                    visible_comments = self.extract_visible_comments_from_dom(page)
                    print(f"[SCRAPE] Synlige comments fundet i DOM: {len(visible_comments)}")

                    added_this_round = 0

                    for c in visible_comments:
                        normalized = self.normalize_comment(c)
                        if self.is_valid_comment(normalized):
                            key = self.comment_key(normalized)
                            if key not in all_comments:
                                all_comments[key] = normalized
                                added_this_round += 1

                    current_unique_count = len(all_comments)

                    print(f"[SCRAPE] Nye unikke kommentarer: {added_this_round}")
                    print(f"[SCRAPE] Samlet unikke kommentarer: {current_unique_count}")

                    if current_unique_count == previous_unique_count:
                        stable_rounds += 1
                        print(f"[SCRAPE] Ingen vækst. Stable rounds: {stable_rounds}/{stable_rounds_required}")
                    else:
                        stable_rounds = 0
                        previous_unique_count = current_unique_count
                        print("[SCRAPE] Der kom nye kommentarer ind.")

                    if stable_rounds >= stable_rounds_required:
                        print("[SCRAPE] Stopper: ingen vækst i tilstrækkeligt mange runder.")
                        break

                    scrolled = self.scroll_comment_panel(
                        page,
                        scroll_rounds=2,
                        pause_ms=wait_between_rounds_ms,
                    )
                    print(f"[SCRAPE] Scroll-resultat: {scrolled}")

                final_comments = list(all_comments.values())
                print(f"\n[SCRAPE] Færdig. Samlet antal unikke kommentarer scrapet: {len(final_comments)}")
                print(f"[SCRAPE] TikTok official comment count: {comment_count}")
                return final_comments, comment_count

            finally:
                browser.close()

    def scrape_to_dataframe(
        self,
        video_url: str,
        comment_column: str = "comment_text"
    ) -> Tuple[pd.DataFrame, Optional[int]]:
        comments, comment_count = self.scrape_comments(video_url=video_url)
        df = self.comments_to_dataframe(comments, comment_column=comment_column)
        return df, comment_count

    def save_comments_to_json(self, comments: List[Dict], output_path: str = "output_comments.json"):
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(comments, f, ensure_ascii=False, indent=2)