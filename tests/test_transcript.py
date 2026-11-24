import pytest

from youtube_analyser.models import TranscriptSegment
from youtube_analyser.transcript import extract_video_id, segment_windows


@pytest.mark.parametrize(
    ("url", "video_id"),
    [
        ("https://www.youtube.com/watch?v=yGgq0sB9HeA", "yGgq0sB9HeA"),
        ("https://youtu.be/yGgq0sB9HeA?t=20", "yGgq0sB9HeA"),
        ("https://www.youtube.com/shorts/yGgq0sB9HeA", "yGgq0sB9HeA"),
    ],
)
def test_extract_video_id(url: str, video_id: str) -> None:
    assert extract_video_id(url) == video_id


def test_extract_video_id_rejects_non_youtube_url() -> None:
    with pytest.raises(ValueError):
        extract_video_id("https://example.com/video")


def test_segment_windows_preserves_order() -> None:
    segments = [
        TranscriptSegment(start=0, duration=1, text="one"),
        TranscriptSegment(start=1, duration=1, text="two"),
        TranscriptSegment(start=2, duration=1, text="three"),
    ]
    windows = segment_windows(segments, max_chars=5)
    assert [[item.text for item in window] for window in windows] == [["one"], ["two"], ["three"]]
