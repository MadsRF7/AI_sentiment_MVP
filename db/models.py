from sqlalchemy import Column, Integer, String, Text, DateTime, func # Import necessary SQLAlchemy components
from db.database import Base # Import the Base class from the database module

# Define the CommentAnalysis model, 
# which represents the structure of the comment_analysis table in the database
class CommentAnalysis(Base):
    __tablename__ = "comment_analysis"

    id = Column(Integer, primary_key=True, index=True)
    source_file = Column(String(255), nullable=True)
    comment_id = Column(String(255), nullable=False, index=True)
    comment_text = Column(Text, nullable=False)

    sentiment = Column(String(50), nullable=True, index=True)
    reason = Column(String(255), nullable=True)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)