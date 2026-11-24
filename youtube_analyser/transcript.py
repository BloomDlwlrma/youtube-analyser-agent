from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import yt_dlp

from .models import TranscriptSegment, VideoMetadata


def extract_video_id(url: str) -> str:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    video_id = ""
    if parsed.scheme not in ("http", "https") or parsed.username or parsed.password or parsed.port:
        raise ValueError("Provide a standard YouTube video URL")
    if host in ("youtube.com", "www.youtube.com", "m.youtube.com"):
        if parsed.path == "/watch":
            ids = parse_qs(parsed.query).get("v", [])
            video_id = ids[0] if len(ids) == 1 else ""
        elif parsed.path.startswith(("/shorts/", "/embed/")):
            video_id = parsed.path.split("/")[-1]
    elif host == "youtu.be":
        video_id = parsed.path.removeprefix("/")
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        raise ValueError("Provide a YouTube video URL with a valid video ID")
    return video_id


def canonical_url(url: str) -> str:
    return f"https://www.youtube.com/watch?v={extract_video_id(url)}"


def get_metadata(url: str) -> VideoMetadata:
    video_id = extract_video_id(url)
    url = canonical_url(url)
    try:
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True,
                               "noplaylist": True}) as client:
            info = client.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as exc:
        raise RuntimeError(f"Unable to read YouTube metadata: {exc}") from exc
    return VideoMetadata(video_id=video_id, title=info.get("title", ""),
                         channel=info.get("channel") or info.get("uploader", ""),
                         duration_seconds=info.get("duration"), url=url)


def _caption_segments(url: str, language: str, directory: Path) -> list[TranscriptSegment]:
    options = {
        "quiet": True, "no_warnings": True, "skip_download": True, "noplaylist": True,
        "writesubtitles": True, "writeautomaticsub": True, "subtitlesformat": "json3",
        "subtitleslangs": [language, f"{language}-.*"],
        "outtmpl": str(directory / "caption.%(ext)s"),
    }
    with yt_dlp.YoutubeDL(options) as client:
        client.extract_info(url, download=True)
    files = sorted(directory.glob("caption.*.json3"),
                   key=lambda p: (p.name != f"caption.{language}.json3", p.name))
    if not files:
        return []
    data = json.loads(files[0].read_text(encoding="utf-8"))
    segments = []
    for event in data.get("events", []):
        text = "".join(part.get("utf8", "") for part in event.get("segs", [])).strip()
        if text:
            segments.append(TranscriptSegment(start=event.get("tStartMs", 0) / 1000,
                                              duration=event.get("dDurationMs", 0) / 1000,
                                              text=text))
    if not segments:
        raise RuntimeError("Downloaded captions contain no usable text")
    return segments


def _whisper_segments(url: str, model_name: str, language: str, directory: Path) -> list[TranscriptSegment]:
    from faster_whisper import WhisperModel

    options = {"format": "bestaudio/best", "outtmpl": str(directory / "audio.%(ext)s"),
               "quiet": True, "no_warnings": True, "noplaylist": True}
    with yt_dlp.YoutubeDL(options) as client:
        info = client.extract_info(url, download=True)
        downloaded = client.prepare_filename(info)
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(downloaded, language=language.split("-")[0], vad_filter=True)
    result = [TranscriptSegment(start=float(segment.start),
                                duration=float(segment.end - segment.start),
                                text=segment.text.strip())
              for segment in segments if segment.text.strip()]
    if not result:
        raise RuntimeError("Whisper returned an empty transcript")
    return result


def get_transcript(url: str, language: str = "en",
                   whisper_model: str = "small") -> tuple[list[TranscriptSegment], str]:
    url = canonical_url(url)
    with tempfile.TemporaryDirectory(prefix="youtube-analyser-") as temp_dir:
        try:
            directory = Path(temp_dir)
            segments = _caption_segments(url, language, directory)
            if segments:
                return segments, "captions"
            return _whisper_segments(url, whisper_model, language, directory), "whisper"
        except (yt_dlp.utils.DownloadError, OSError, ValueError, RuntimeError) as exc:
            raise RuntimeError(f"Transcript retrieval failed: {exc}") from exc


def format_transcript(segments: list[TranscriptSegment]) -> str:
    return "\n".join(f"[{segment.start:.1f}s] {segment.text}" for segment in segments)
