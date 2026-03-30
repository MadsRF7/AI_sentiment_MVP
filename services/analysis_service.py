import hashlib
import re

from config import Settings


class AnalysisService:
    def __init__(
        self,
        sentiment_service,
        analysis_run_repo,
        analysis_result_repo,
    ):
        self.sentiment_service = sentiment_service
        self.analysis_run_repo = analysis_run_repo
        self.analysis_result_repo = analysis_result_repo

    def normalize_comment(self, text: str) -> str:
        text = str(text).strip().lower()
        text = re.sub(r"\s+", " ", text)
        return text

    def make_comment_hash(self, text: str) -> str:
        normalized = self.normalize_comment(text)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def run_analysis(self, df, source_file, progress_callback=None):
        results = []
        result_rows = []

        total_rows = len(df)
        total = len(df)

        run = self.analysis_run_repo.create_run(
            original_file_name=source_file,
            total_rows=total_rows,
            valid_comment_rows=total_rows,
            file_hash=None,
        )

        try:
            for idx, row in df.iterrows():
                text = row[Settings.COMMENT_COLUMN]
                row_index = idx + 1
                comment_hash = self.make_comment_hash(text)

                try:
                    result = self.sentiment_service.classify_comment(text)
                    sentiment = result["sentiment"]
                    reason = result["reason"]

                except Exception as e:
                    sentiment = "neutral"
                    reason = f"Analysis error: {str(e)}"

                result_row = {
                    "run_id": run.id,
                    "row_index": row_index,
                    "platform_comment_id": None,
                    "comment_text": text,
                    "comment_hash": comment_hash,
                    "sentiment": sentiment,
                    "reason": reason,
                    "model_name": "gpt-4.1-mini",
                }

                result_rows.append(result_row)

                enriched_row = row.to_dict()
                enriched_row["sentiment"] = sentiment
                enriched_row["reason"] = reason
                results.append(enriched_row)

                if progress_callback:
                    progress_callback((idx + 1) / total)

            self.analysis_result_repo.save_results_bulk(result_rows)
            self.analysis_run_repo.mark_completed(run.id)

            return run.id, results

        except Exception:
            self.analysis_run_repo.mark_failed(run.id)
            raise