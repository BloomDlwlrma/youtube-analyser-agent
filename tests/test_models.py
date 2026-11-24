import pytest
from pydantic import ValidationError

from youtube_analyser.models import AnalysisResult, NarrativeBeat, VideoMetadata


def test_analysis_result_requires_evidence_for_beats() -> None:
    metadata = VideoMetadata(video_id="yGgq0sB9HeA", url="https://youtu.be/yGgq0sB9HeA")
    with pytest.raises(ValidationError):
        AnalysisResult(
            metadata=metadata,
            language="zh",
            summary="summary",
            narrative_beats=[{"type": "hook", "start": 0, "end": 10}],
            model="test",
        )


def test_narrative_beat_accepts_known_type() -> None:
    beat = NarrativeBeat(
        type="hook",
        start=0,
        end=10,
        evidence="Exact evidence",
        explanation="Why it matters",
    )
    assert beat.type == "hook"
