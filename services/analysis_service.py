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
        text = str(text or "").strip().lower()
        text = re.sub(r"\s+", " ", text)
        return text

    def make_comment_hash(self, text: str, author: str | None = None) -> str:
        normalized_text = self.normalize_comment(text)
        normalized_author = self.normalize_comment(author or "")
        raw = f"{normalized_author}||{normalized_text}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def run_analysis(self, df, source_file, progress_callback=None):
        results = []
        result_rows = []

        total_rows = len(df)

        run = self.analysis_run_repo.create_run(
            original_file_name=source_file,
            total_rows=total_rows,
            valid_comment_rows=total_rows,
            file_hash=None,
        )
        run_id = run.id

        seen_hashes = set()
        processed_count = 0

        try:
            for idx, row in df.iterrows():
                text = row.get(Settings.COMMENT_COLUMN, "")
                author = row.get("author", "")

                text = str(text or "").strip()
                author = str(author or "").strip()

                if not text:
                    continue

                comment_hash = self.make_comment_hash(text=text, author=author)

                # Skip duplicates within the same analysis run
                if comment_hash in seen_hashes:
                    continue

                seen_hashes.add(comment_hash)

                row_index = idx + 1

                try:
                    result = self.sentiment_service.classify_comment(text)
                    sentiment = result["sentiment"]
                    reason = result["reason"]
                except Exception as e:
                    sentiment = "neutral"
                    reason = f"Analysis error: {str(e)}"

                result_row = {
                    "run_id": run_id,
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
                enriched_row["comment_hash"] = comment_hash
                results.append(enriched_row)

                processed_count += 1

                if progress_callback and total_rows > 0:
                    progress_callback((idx + 1) / total_rows)

            self.analysis_result_repo.save_results_bulk(result_rows)
            self.analysis_run_repo.mark_completed(run_id)

            return run_id, results

        except Exception:
            # Brug run_id direkte i stedet for run.id
            self.analysis_run_repo.mark_failed(run_id)
            raise