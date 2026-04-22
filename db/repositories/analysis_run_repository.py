import uuid
from sqlalchemy import (
    func,
)  # Import func for using SQL functions like now() in the model
from db.models import AnalysisRun


# Repository class for managing AnalysisRun records in the database
class AnalysisRunRepository:
    def __init__(self, session):
        self.session = session

    # Method to create a new analysis run record in the database with the provided details
    def create_run(
        self, original_file_name, total_rows, valid_comment_rows, file_hash=None
    ):
        run = AnalysisRun(
            run_uuid=str(uuid.uuid4()),
            original_file_name=original_file_name,
            file_hash=file_hash,
            total_rows=total_rows,
            valid_comment_rows=valid_comment_rows,
            status="processing",
        )
        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)
        return run

    # Method to mark an analysis run as completed in the database
    def mark_completed(self, run_id):
        run = self.session.get(AnalysisRun, run_id)
        if run:
            run.status = "completed"
            run.completed_at = func.now()
            self.session.commit()

    # Method to mark an analysis run as failed in the database
    def mark_failed(self, run_id):
        run = self.session.get(AnalysisRun, run_id)
        if run:
            run.status = "failed"
            self.session.commit()

    # Method to retrieve the latest completed analysis run from the database
    def get_latest_completed_run(self):
        return (
            self.session.query(AnalysisRun)
            .filter(AnalysisRun.status == "completed")
            .order_by(AnalysisRun.created_at.desc())
            .first()
        )
