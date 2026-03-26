import os # added to access environment variables, such as the OpenAI API key, which is essential for the app's functionality
from dotenv import load_dotenv # added to load environment variables from .env file, making it easier to manage API keys and other sensitive information

load_dotenv()

class Settings:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    PAGE_TITLE = "AI Sentiment Analysis"
    PAGE_ICON = "🤖"
    LAYOUT = "wide"

    COMMENT_COLUMN = "Comment" # updated to match the actual column name in the dataset, ensuring the app can correctly identify and process the comments for sentiment analysis
