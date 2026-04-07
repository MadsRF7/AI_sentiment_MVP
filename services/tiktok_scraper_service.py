import json
import os
from typing import List, Dict

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

    def scrape_comments(
        self,
        video_url: str,
        rounds: int = 3,
        scroll_amount: int = 1000,
        wait_ms: int = 2000,
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
                page.goto(video_url, wait_until="domcontentloaded")
                page.wait_for_timeout(6000)

                self.pause_video(page)
                page.wait_for_timeout(1500)

                # TikTok kræver ofte manuel åbning af kommentarpanel / login
                print("Åbn kommentarpanelet manuelt nu, og scroll lidt i det.")
                input("Tryk Enter når kommentarpanelet er åbent og kommentarer er synlige...")

                for i in range(rounds):
                    response = page.query_data(QUERY)
                    comments = response.get("comments", [])

                    print(f"Runde {i + 1}: rå antal = {len(comments)}")

                    for c in comments:
                        normalized = self.normalize_comment(c)

                        if self.is_valid_comment(normalized):
                            key = self.comment_key(normalized)
                            all_comments[key] = normalized

                    page.mouse.move(1250, 500)
                    page.mouse.wheel(0, scroll_amount)
                    page.wait_for_timeout(wait_ms)

                final_comments = list(all_comments.values())
                return final_comments

            finally:
                browser.close()

    def comments_to_dataframe(self, comments: List[Dict], comment_column: str = "comment_text") -> pd.DataFrame:
        if not comments:
            return pd.DataFrame(columns=[comment_column, "author"])

        df = pd.DataFrame(comments)
        df = df.rename(columns={"text": comment_column})
        return df[[comment_column, "author"]]

    def scrape_to_dataframe(self, video_url: str, comment_column: str = "comment_text") -> pd.DataFrame:
        comments = self.scrape_comments(video_url=video_url)
        return self.comments_to_dataframe(comments, comment_column=comment_column)

    def save_comments_to_json(self, comments: List[Dict], output_path: str = "output_comments.json"):
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(comments, f, ensure_ascii=False, indent=2)