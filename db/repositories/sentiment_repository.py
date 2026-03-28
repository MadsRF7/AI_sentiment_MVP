import pandas as pd
from db.models import SentimentResult
from sqlalchemy import select
from db.models import SentimentResult, Comment, Video # Import the SentimentResult, Comment, and Video models from the models module


# Repository for handling sentiment analysis results in the database.
class SentimentRepository:
    def __init__(self, session):
        self.session = session

# Save the sentiment analysis result for a given comment.
    def save_sentiment(self, comment_id: int, sentiment: str, reason: str, model_name: str):
        row = SentimentResult(
            comment_id=comment_id,
            sentiment=sentiment,
            reason=reason,
            model_name=model_name,
        )

        self.session.add(row)
        self.session.commit()

    def fetch_analysis_overview_as_dataframe(self) -> pd.DataFrame:
        stmt = (
            select(
                Video.title.label("video_title"),
                Comment.platform_comment_id,
                Comment.text,
                SentimentResult.sentiment,
                SentimentResult.reason,
                SentimentResult.model_name,
                SentimentResult.created_at,
            )
            .join(Comment, SentimentResult.comment_id == Comment.id)
            .join(Video, Comment.video_id == Video.id)
            .order_by(SentimentResult.created_at.desc())
        )

        rows = self.session.execute(stmt).all()

        data = [
            {
                "video_title": row.video_title,
                "platform_comment_id": row.platform_comment_id,
                "comment_text": row.text,
                "sentiment": row.sentiment,
                "reason": row.reason,
                "model_name": row.model_name,
                "created_at": row.created_at,
            }
            for row in rows
        ]

        return pd.DataFrame(data)