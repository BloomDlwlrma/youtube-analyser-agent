import pytest

from youtube_analyser.models import TranscriptSegment
from youtube_analyser.transcript import (
    _invidious_caption_segments,
    _parse_vtt,
    _yt_dlp_options,
    extract_video_id,
    segment_windows,
)


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


def test_parse_vtt_preserves_timestamps() -> None:
    segments = _parse_vtt(
        """WEBVTT

00:00:01.000 --> 00:00:03.500
Hello <b>world</b>

"""
    )
    assert segments[0].start == 1
    assert segments[0].duration == 2.5
    assert segments[0].text == "Hello world"


def test_yt_dlp_options_support_browser_cookies_and_po_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("YTDLP_COOKIES_FROM_BROWSER", "chrome:Default")
    monkeypatch.setenv("YTDLP_PO_TOKEN", "token")
    monkeypatch.setenv("YTDLP_PO_TOKEN_CONTEXT", "web.gvs")
    options = _yt_dlp_options()
    assert options["cookiesfrombrowser"] == ("chrome", "Default")
    assert options["extractor_args"] == {"youtube": {"po_token": "web.gvs+token"}}


def test_invidious_caption_fallback_reads_caption_url(monkeypatch: pytest.MonkeyPatch) -> None:
    class Response:
        def __init__(self, payload: dict | None = None, text: str = "") -> None:
            self._payload = payload
            self.text = text

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return self._payload or {}

    responses = iter(
        [
            Response({"captions": [{"languageCode": "en", "url": "https://instance/caption.vtt"}]}),
            Response(text="00:00:00.000 --> 00:00:02.000\nA caption\n"),
        ]
    )
    monkeypatch.setattr("youtube_analyser.transcript._invidious_instances", lambda: ["https://instance"])
    monkeypatch.setattr("youtube_analyser.transcript.httpx.get", lambda *args, **kwargs: next(responses))
    segments = _invidious_caption_segments("yGgq0sB9HeA", "en")
    assert segments[0].text == "A caption"
