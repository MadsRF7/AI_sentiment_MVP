import pandas as pd
from sqlalchemy import select
from db.models import CommentAnalysis


# Repository class for managing database operations related to comment analysis results,
# providing methods for inserting new results and querying existing data
class CommentRepository:
    # Initialize the repository with a database session, 
    # which will be used for all database operations
    def __init__(self, session):
        self.session = session

# Method to save a new comment analysis result to the database,
# taking the source file, comment ID, comment text, sentiment, and reason as parameters
    def save_analysis_row(
            self,
            source_file: str,
            comment_id: str,
            comment_text: str,
            sentiment: str,
            reason: str,
    ) -> None:
        row = CommentAnalysis(
            source_file=source_file,
            comment_id=comment_id,
            comment_text=comment_text,
            sentiment=sentiment,
            reason=reason,
        )
        self.session.add(row)
        self.session.commit()

# Method to fetch all comment analysis results from the database 
# and return them as a pandas DataFrame,
# which allows for easy data manipulation and analysis using pandas' powerful features
    def fetch_all_as_dataframe(self) -> pd.DataFrame:
        stmt = select(CommentAnalysis)
        rows = self.session.execute(stmt).scalars().all()

        data = [
            {
                "id": row.id,
                "source_file": row.source_file,
                "comment_id": row.comment_id,
                "comment_text": row.comment_text,
                "sentiment": row.sentiment,
                "reason": row.reason,
                "created_at": row.created_at,
            }
            for row in rows
        ]

        return pd.DataFrame(data)
    
    # ----------- Final note on the repository pattern -----------
    # repository ensures that all database interactions related to comment analysis results 
    # are encapsulated within a single class (the CommentRepository),
    # making it easier to manage and maintain the codebase 
    # as the application evolves and new features are added in the future.
    # ------------------------------------------------------------ #