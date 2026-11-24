import json
from pathlib import Path

from youtube_analyser.models import AnalysisResult


def test_synthetic_example() -> None:
    fixture = Path(__file__).parents[1] / "data" / "examples" / "synthetic.json"
    result = AnalysisResult.model_validate(json.loads(fixture.read_text(encoding="utf-8")))
    assert result.metadata.title == "Synthetic example"
    assert result.narrative_beats[0].type == "cta"
    assert result.model == "fixture-stub"
