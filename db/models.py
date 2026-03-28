from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func # Import necessary SQLAlchemy components
from sqlalchemy.orm import relationship # Import relationship for defining relationships between tables
from db.database import Base # Import the Base class from the database module



# Define the Video model, which represents a video in the database 
# and includes fields for id, platform, platform_video_id, title, created_at, 
# and a relationship to comments.
class Video(Base):
    __tablename__ = 'videos' # Define the table name for the Video model

    id = Column(Integer, primary_key=True)
    platform = Column(String(50), nullable=False)
    platform_video_id = Column(String(255), nullable=True, unique=True)
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=func.now()) # Automatically set the created_at field to the current time

    comments = relationship('Comment', back_populates='video') # Define a relationship to the Comment model


# Define the Comment model, 
# which represents a comment on a video in the database 
# and includes fields for id, platform_comment_id, video_id, text, created_at, ingested
class Comment(Base):
    __tablename__ = 'comments' # Define the table name for the Comment model

    id = Column(Integer, primary_key=True)
    platform_comment_id = Column(String(255), unique=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id"))
    text = Column(Text, nullable=False)

# ingested_at is the time when the comment was ingested into our system, which may be different from when it was created on the platform.
    created_at = Column(DateTime, server_default=func.now())
    ingested_at = Column(DateTime, server_default=func.now())

    video = relationship("Video", back_populates="comments")
    sentiments = relationship("SentimentResult", back_populates="comment")


# Define the SentimentResult model, 
# which represents the result of a sentiment analysis on a comment in the database
class SentimentResult(Base):
    __tablename__ = 'sentiment_results' # Define the table name for the SentimentResult model

    id = Column(Integer, primary_key=True)
    comment_id = Column(Integer, ForeignKey("comments.id"))

    sentiment = Column(String(50), nullable=False) # e.g., 'positive', 'negative', 'neutral'
    reason = Column(String(255), nullable=True) # Optional field to provide a reason for the sentiment classification
    model_name = Column(String(100), nullable=False) # The name of the model that generated the sentiment result

    created_at = Column(DateTime, server_default=func.now()) # Automatically set the created_at field to the current time

    comment = relationship("Comment", back_populates="sentiments")