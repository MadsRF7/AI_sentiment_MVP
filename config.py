import os # added to access environment variables, such as the OpenAI API key, which is essential for the app's functionality
from dotenv import load_dotenv # added to load environment variables from .env file, making it easier to manage API keys and other sensitive information

load_dotenv()

class Settings:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    PAGE_TITLE = "AI Sentiment Analysis"
    PAGE_ICON = "🤖"
    LAYOUT = "wide"

# updated to match the actual column name in the dataset, 
# ensuring the app can correctly identify 
# and process the comments for sentiment analysis
    COMMENT_COLUMN = "Comment"

# added database configuration settings, 
# allowing the app to connect to a MySQL database for storing and retrieving sentiment analysis results, 
# which is crucial for data persistence and future analysis
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", 3306))
    DB_NAME = os.getenv("DB_NAME", "sentiment_app")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "21mttNZ!")

# added a method to construct the database URL, 
# which is necessary for establishing a connection to the MySQL database 
# using an ORM like SQLAlchemy 
# (ORM = Object-Relational Mapping, 
# a technique that allows developers to interact with a database using an object-oriented paradigm, 
# rather than writing raw SQL queries)
    @classmethod
    def database_url(cls) -> str:
        return (
            f"mysql+pymysql://{cls.DB_USER}:{cls.DB_PASSWORD}"
            f"@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}?charset=utf8mb4"
        )
