from sqlalchemy import create_engine # for creating the database engine
from sqlalchemy.orm import declarative_base, sessionmaker # for defining the database models and managing database sessions
from config import Settings

Base = declarative_base() # base class for our database models

# create the database engine using the database URL from the settings, 
# which allows us to connect to the MySQL database
engine = create_engine(
    Settings.database_url(),
    echo=False,
    pool_pre_ping=True,
)

# create the database tables based on the defined models, 
# ensuring that the database schema is set up correctly for storing sentiment analysis results
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# function to get a new database session, 
# which is essential for performing database operations 
# such as inserting new sentiment analysis results or querying existing data
def get_session():
    return SessionLocal()