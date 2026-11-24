from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
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
        with yt_dlp.YoutubeDL(_yt_dlp_options(skip_download=True)) as client:
            info = client.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as exc:
        try:
            info = _invidious_request(f"/api/v1/videos/{video_id}")
        except RuntimeError as fallback_error:
            raise RuntimeError(
                f"Unable to read YouTube metadata with yt-dlp ({exc}) or Invidious ({fallback_error})"
            ) from fallback_error
    return VideoMetadata(video_id=video_id, title=info.get("title", ""),
                         channel=info.get("author") or info.get("channel") or info.get("uploader", ""),
                         duration_seconds=info.get("lengthSeconds") or info.get("duration"), url=url)


def _yt_dlp_options(**overrides: object) -> dict[str, object]:
    options: dict[str, object] = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }
    cookies_from_browser = os.getenv("YTDLP_COOKIES_FROM_BROWSER")
    if cookies_from_browser:
        browser, _, profile = cookies_from_browser.partition(":")
        options["cookiesfrombrowser"] = (browser, profile) if profile else (browser,)
    cookies_file = os.getenv("YTDLP_COOKIES_FILE")
    if cookies_file:
        options["cookiefile"] = cookies_file
    po_token = os.getenv("YTDLP_PO_TOKEN")
    if po_token:
        context = os.getenv("YTDLP_PO_TOKEN_CONTEXT", "web.gvs")
        options["extractor_args"] = {"youtube": {"po_token": f"{context}+{po_token}"}}
    options.update(overrides)
    return options


def _invidious_instances() -> list[str]:
    configured = os.getenv("INVIDIOUS_INSTANCE_URLS", "")
    if configured:
        return [item.rstrip("/") for item in configured.split(",") if item.strip()]
    if os.getenv("INVIDIOUS_DISCOVERY", "true").lower() not in {"1", "true", "yes"}:
        return []
    try:
        response = httpx.get("https://api.invidious.io/instances.json", timeout=8)
        response.raise_for_status()
        instances = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise RuntimeError(f"Unable to discover Invidious instances: {exc}") from exc
    result = []
    for values in instances.values():
        if not values:
            continue
        uri = values[0].get("uri")
        if uri and uri.startswith("https://"):
            result.append(uri.rstrip("/"))
    return result[:8]


def _invidious_request(path: str) -> dict:
    failures: list[str] = []
    for instance in _invidious_instances():
        try:
            response = httpx.get(f"{instance}{path}", timeout=12)
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, dict):
                return payload
            failures.append(f"{instance}: non-object response")
        except (httpx.HTTPError, ValueError) as exc:
            failures.append(f"{instance}: {exc}")
    detail = "; ".join(failures) or "no Invidious instances configured"
    raise RuntimeError(detail)


_VTT_TIMESTAMP = re.compile(
    r"(?P<start>\d{2,}:\d{2}:\d{2}(?:\.\d{3})?)\s*-->\s*"
    r"(?P<end>\d{2}:\d{2}:\d{2}(?:\.\d{3})?)"
)


def _vtt_seconds(value: str) -> float:
    hours, minutes, seconds = value.split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def _parse_vtt(text: str) -> list[TranscriptSegment]:
    lines = [line.strip() for line in text.splitlines()]
    segments: list[TranscriptSegment] = []
    current: tuple[float, float] | None = None
    caption_lines: list[str] = []
    for line in lines + [""]:
        match = _VTT_TIMESTAMP.search(line)
        if match:
            current = (_vtt_seconds(match.group("start")), _vtt_seconds(match.group("end")))
            caption_lines = []
            continue
        if line or current is None:
            if line and current is not None:
                caption_lines.append(re.sub(r"<[^>]+>", "", line))
            continue
        if current and caption_lines:
            caption = " ".join(caption_lines).strip()
            if caption:
                start, end = current
                segments.append(TranscriptSegment(start=start, duration=max(0, end - start), text=caption))
        current = None
        caption_lines = []
    return segments


def _invidious_caption_segments(video_id: str, language: str) -> list[TranscriptSegment]:
    encoded_language = language.replace("-", "%2D")
    failures: list[str] = []
    for instance in _invidious_instances():
        try:
            response = httpx.get(
                f"{instance}/api/v1/captions/{video_id}?lang={encoded_language}",
                timeout=12,
            )
            response.raise_for_status()
            payload = response.json()
            caption = payload.get("caption")
            if isinstance(caption, str):
                segments = _parse_vtt(caption)
            else:
                tracks = payload.get("captions") or []
                track = next(
                    (item for item in tracks if item.get("languageCode") == language),
                    tracks[0] if tracks else None,
                )
                caption_url = track.get("url") if track else None
                caption_response = httpx.get(caption_url, timeout=12) if caption_url else None
                if caption_response is not None:
                    caption_response.raise_for_status()
                    segments = _parse_vtt(caption_response.text)
                else:
                    segments = []
            if segments:
                return segments
            failures.append(f"{instance}: no usable captions")
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            failures.append(f"{instance}: {exc}")
    detail = "; ".join(failures) or "no Invidious instances configured"
    raise RuntimeError(detail)


def _caption_segments(url: str, language: str, directory: Path) -> list[TranscriptSegment]:
    options = _yt_dlp_options(
        writesubtitles=True,
        writeautomaticsub=True,
        subtitlesformat="json3",
        subtitleslangs=[language, f"{language}-.*"],
        outtmpl=str(directory / "caption.%(ext)s"),
    )
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

    options = _yt_dlp_options(format="bestaudio/best", outtmpl=str(directory / "audio.%(ext)s"))
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
            try:
                segments = _caption_segments(url, language, directory)
            except (yt_dlp.utils.DownloadError, OSError, RuntimeError) as yt_error:
                try:
                    segments = _invidious_caption_segments(extract_video_id(url), language)
                except RuntimeError as invidious_error:
                    raise RuntimeError(
                        f"caption providers failed: yt-dlp={yt_error}; invidious={invidious_error}"
                    ) from invidious_error
            if segments:
                return segments, "captions"
            return _whisper_segments(url, whisper_model, language, directory), "whisper"
        except (yt_dlp.utils.DownloadError, OSError, ValueError, RuntimeError) as exc:
            raise RuntimeError(f"Transcript retrieval failed: {exc}") from exc


def format_transcript(segments: list[TranscriptSegment]) -> str:
    return "\n".join(f"[{segment.start:.1f}s] {segment.text}" for segment in segments)


def segment_windows(
    segments: list[TranscriptSegment], max_chars: int = 12000
) -> list[list[TranscriptSegment]]:
    if max_chars < 1:
        raise ValueError("max_chars must be positive")
    windows: list[list[TranscriptSegment]] = []
    current: list[TranscriptSegment] = []
    current_chars = 0
    for segment in segments:
        if current and current_chars + len(segment.text) > max_chars:
            windows.append(current)
            current = []
            current_chars = 0
        current.append(segment)
        current_chars += len(segment.text)
    if current:
        windows.append(current)
    return windows
