from db.models import Video # Import the Video model from the models module


# The VideoRepository class provides methods to interact with the Video model in the database,
# such as retrieving an existing video or creating a new one if it doesn't exist.
class VideoRepository:
    def __init__(self, session):
        self.session = session

    def get_or_create_video(
        self,
        platform: str,
        title: str = None,
        platform_video_id: str = None,
    ):
        query = self.session.query(Video).filter_by(
            platform=platform,
            title=title,
            platform_video_id=platform_video_id,
        )

        video = query.first()

        if not video:
            video = Video(
                platform=platform,
                platform_video_id=platform_video_id,
                title=title,
            )
            self.session.add(video)
            self.session.commit()
            self.session.refresh(video)

        return video