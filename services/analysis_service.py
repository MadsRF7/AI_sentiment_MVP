import pandas as pd
from config import Settings


# AnalysisService class is responsible for performing sentiment analysis on comments 
# and saving the results to the repository.
class AnalysisService:
    def __init__ (self, sentiment_analysis, comment_repository):
        self.sentiment_analysis = sentiment_analysis
        self.comment_repository = comment_repository

# The run_analysis method processes each comment in the DataFrame, classifies its sentiment,
# and saves the results to the repository. 
# It also supports a progress callback to track the analysis
    def run_analysis(self, df: pd.DataFrame, source_file: str, progress_callback=None) -> pd.DataFrame:
        results = []
        total = len(df)

        for idx, row in df.iterrows():
            comment_id = row[Settings.COMMENT_COLUMN]
            comment_text = row[Settings.COMMENT_COLUMN]

            try:
                result = self.sentiment_analysis.classify_comment(comment_text)
                sentiment = result["sentiment"]
                reason = result["reason"]
            except Exception as e:
                sentiment = "error"
                reason = str(e)

            enriched_row = row.to_dict()
            enriched_row["sentiment"] = sentiment
            enriched_row["reason"] = reason
            results.append(enriched_row)

            self.comment_repository.save_analysis_row(
                source_file=source_file,
                comment_id=comment_id,
                comment_text=comment_text,
                sentiment=sentiment,
                reason=reason,
            )

            if progress_callback is not None and total > 0:
                progress_callback((idx + 1) / total)

            return pd.DataFrame(results)