from config import Settings


class AnalysisService:
    def __init__(
        self,
        sentiment_service,
        video_repo,
        comment_repo,
        sentiment_repo,
    ):
        self.sentiment_service = sentiment_service
        self.video_repo = video_repo
        self.comment_repo = comment_repo
        self.sentiment_repo = sentiment_repo

    def run_analysis(self, df, source_file, progress_callback=None):
        results = []
        total = len(df)

        video = self.video_repo.get_or_create_video(
            platform="csv",
            title=source_file,
            platform_video_id=source_file,
        )

        for idx, row in df.iterrows():
            text = row[Settings.COMMENT_COLUMN]

            platform_comment_id = f"{source_file}_{idx}"

            comment = self.comment_repo.get_or_create_comment(
                platform_comment_id=platform_comment_id,
                video_id=video.id,
                text=text,
            )

            try:
                result = self.sentiment_service.classify_comment(text)

                sentiment = result["sentiment"]
                reason = result["reason"]

                self.sentiment_repo.save_sentiment(
                    comment_id=comment.id,
                    sentiment=sentiment,
                    reason=reason,
                    model_name="gpt-4.1-mini",
                )

            except Exception as e:
                sentiment = "error"
                reason = str(e)

            enriched_row = row.to_dict()
            enriched_row["sentiment"] = sentiment
            enriched_row["reason"] = reason
            results.append(enriched_row)

            if progress_callback:
                progress_callback((idx + 1) / total)

        return results