from db.models import Comment


# The CommentRepository class provides methods to interact with the Comment model in the database,
# such as retrieving an existing comment or creating a new one if it doesn't exist.
class CommentRepository:
    def __init__(self, session):
        self.session = session

    # The get_or_create_comment method retrieves a comment by its platform_comment_id.
    # If the comment does not exist, it creates a new one with the provided video_id and text.
    def get_or_create_comment(self, platform_comment_id: str, video_id: int, text: str):
        comment = (
            self.session.query(Comment)
            .filter_by(platform_comment_id=platform_comment_id)
            .first()
        )

        if comment:
            return comment

        # If the comment does not exist, create a new one with the provided video_id and text.
        # OBS!!!!! Should maybe be deleted, as we don't want to create comments that don't exist on the platform.
        # Instead, we should only create comments that we have ingested from the platform.
        comment = Comment(
            platform_comment_id=platform_comment_id,
            video_id=video_id,
            text=text,
        )

        self.session.add(comment)
        self.session.commit()

        return comment
