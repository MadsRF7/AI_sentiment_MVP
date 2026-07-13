from app.services.analysis_service import AnalysisService


def test_make_comment_hash_same_text_and_author_gives_same_hash():
    service = AnalysisService(None, None, None)

    h1 = service.make_comment_hash(" Hello  world ", "Alice")
    h2 = service.make_comment_hash("hello world", "alice")

    assert h1 == h2
