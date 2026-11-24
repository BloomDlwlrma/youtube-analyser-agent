from __future__ import annotations

import json
from pathlib import Path

from .analysis import analyze
from .models import AnalysisResult
from .transcript import get_metadata, get_transcript


def run_analysis(
    url: str,
    language: str = "zh",
    model: str = "llama3.1:8b",
    whisper_model: str = "small",
    output_dir: str | None = None,
) -> AnalysisResult:
    metadata = get_metadata(url)
    segments, source = get_transcript(url, language=language, whisper_model=whisper_model)
    result = analyze(metadata, segments, source, language, model)
    if output_dir:
        save_result(result, output_dir)
    return result


def save_result(result: AnalysisResult, output_dir: str) -> tuple[Path, Path]:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    stem = result.metadata.video_id
    json_path = directory / f"{stem}.json"
    markdown_path = directory / f"{stem}.md"
    json_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    markdown_path.write_text(to_markdown(result), encoding="utf-8")
    return markdown_path, json_path


def to_markdown(result: AnalysisResult) -> str:
    lines = [
        f"# {result.metadata.title or result.metadata.video_id}",
        "",
        f"- Video: {result.metadata.url}",
        f"- Channel: {result.metadata.channel or 'Unknown'}",
        f"- Transcript source: {result.transcript_source}",
        f"- Analysis model: {result.model}",
        "",
        "## Summary",
        "",
        result.summary,
        "",
        "## Key points",
        "",
    ]
    lines.extend(f"- {point}" for point in result.key_points)
    for heading, items in (
        ("Arguments and claims", result.claims),
        ("Examples", result.examples),
        ("Quotes", result.quotes),
        ("Calls to action", result.calls_to_action),
    ):
        lines.extend(["", f"## {heading}", ""])
        lines.extend(f"- {item}" for item in items)
    lines.extend(["", "## Narrative breakdown", ""])
    for beat in result.narrative_beats:
        lines.append(
            f"- **{beat.type}** ({beat.start:.1f}s–{beat.end:.1f}s): "
            f"{beat.explanation} Evidence: “{beat.evidence}”"
        )
    lines.extend(["", "## Reusable template", ""])
    lines.extend(f"{index}. {item}" for index, item in enumerate(result.reusable_template, 1))
    return "\n".join(lines) + "\n"
