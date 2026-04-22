import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    PAGE_TITLE = "AI Sentiment Analysis"
    PAGE_ICON = "🤖"
    LAYOUT = "wide"

    COMMENT_COLUMN = "Comment"

    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", 3306))
    DB_NAME = os.getenv("DB_NAME", "sentiment_app")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")

    @classmethod
    def database_url(cls) -> str:
        if not cls.DB_PASSWORD:
            raise ValueError("DB_PASSWORD is not set")

        return (
            f"mysql+pymysql://{cls.DB_USER}:{cls.DB_PASSWORD}"
            f"@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}?charset=utf8mb4"
        )
