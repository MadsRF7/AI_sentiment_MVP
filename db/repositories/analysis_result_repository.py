from db.models import AnalysisResult


# Repository class for managing AnalysisResult records in the database
class AnalysisResultRepository:
    def __init__(self, session):
        self.session = session

    # Method to save a list of analysis results in bulk to the database
    def save_results_bulk(self, results):
        objects = [AnalysisResult(**result) for result in results]
        self.session.add_all(objects)
        self.session.commit()

    # Method to retrieve all analysis results for a specific analysis run, ordered by row index
    def get_results_for_run(self, run_id):
        return (
            self.session.query(AnalysisResult)
            .filter(AnalysisResult.run_id == run_id)
            .order_by(AnalysisResult.row_index.asc())
            .all()
        )

    # Method to fetch analysis results for a specific run and return them as a pandas DataFrame
    def fetch_results_for_run_as_dataframe(self, run_id):
        import pandas as pd

        rows = self.get_results_for_run(run_id)

        return pd.DataFrame(
            [
                {
                    "row_index": row.row_index,
                    "comment_text": row.comment_text,
                    "sentiment": row.sentiment,
                    "reason": row.reason,
                    "model_name": row.model_name,
                    "created_at": row.created_at,
                }
                for row in rows
            ]
        )
