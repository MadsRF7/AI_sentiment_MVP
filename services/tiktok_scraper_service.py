import json
from typing import List, Dict

import agentql
import pandas as pd
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


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
        headless: bool = False, #--- bool = TRUE -> browser runs in background, FALSE -> browser is visible (for debugging) ---#
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
    def comments_to_dataframe(comments: List[Dict], comment_column: str = "comment_text") -> pd.DataFrame:
        if not comments:
            return pd.DataFrame(columns=[comment_column, "author"])

        df = pd.DataFrame(comments)
        df = df.rename(columns={"text": comment_column})
        return df[[comment_column, "author"]]

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

        # fallback: prøv JS-klik på elementer med comment-tekst/aria-label
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
        selectors = [
            "[data-e2e='comment-list']",
            "[data-e2e='search-comment-list']",
            "div[data-e2e*='comment']",
            "div[class*='DivCommentListContainer']",
            "div[class*='CommentListContainer']",
            "aside",
        ]

        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if locator.count() > 0:
                    return locator
            except Exception:
                pass

        return None

    def scroll_comment_panel(self, page, scroll_rounds: int = 10, pause_ms: int = 1500):
        container = self.find_comment_scroll_container(page)

        if container is not None:
            for _ in range(scroll_rounds):
                try:
                    container.hover()
                    page.mouse.wheel(0, 1500)
                    page.wait_for_timeout(pause_ms)
                except Exception:
                    break
        else:
            # fallback: scroll hele siden
            for _ in range(scroll_rounds):
                page.mouse.wheel(0, 1500)
                page.wait_for_timeout(pause_ms)

    def scrape_comments(
        self,
        video_url: str,
        rounds: int = 3,
        scroll_rounds_between_queries: int = 2,
        wait_after_load_ms: int = 5000,
    ) -> List[Dict]:
        all_comments = {}

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                channel=self.channel,
                headless=self.headless,
                no_viewport=True,
            )

            page = agentql.wrap(browser.new_page())

            try:
                page.goto(video_url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(wait_after_load_ms)

                self.handle_cookie_popup(page)
                self.pause_video(page)

                panel_opened = self.open_comment_panel(page)
                page.wait_for_timeout(2000)

                if not panel_opened:
                    raise RuntimeError("Kunne ikke åbne TikTok kommentarpanelet automatisk.")

                # første scroll for at loade flere kommentarer
                self.scroll_comment_panel(page, scroll_rounds=2, pause_ms=1200)

                for i in range(rounds):
                    try:
                        response = page.query_data(QUERY)
                    except Exception as e:
                        print(f"AgentQL query fejlede i runde {i + 1}: {e}")
                        response = {}

                    comments = response.get("comments", [])
                    print(f"Runde {i + 1}: rå antal = {len(comments)}")

                    for c in comments:
                        normalized = self.normalize_comment(c)

                        if self.is_valid_comment(normalized):
                            key = self.comment_key(normalized)
                            all_comments[key] = normalized

                    self.scroll_comment_panel(
                        page,
                        scroll_rounds=scroll_rounds_between_queries,
                        pause_ms=1500
                    )

                final_comments = list(all_comments.values())
                return final_comments

            finally:
                browser.close()

    def scrape_to_dataframe(self, video_url: str, comment_column: str = "comment_text") -> pd.DataFrame:
        comments = self.scrape_comments(video_url=video_url)
        return self.comments_to_dataframe(comments, comment_column=comment_column)

    def save_comments_to_json(self, comments: List[Dict], output_path: str = "output_comments.json"):
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(comments, f, ensure_ascii=False, indent=2)