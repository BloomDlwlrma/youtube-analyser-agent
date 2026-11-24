from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


BeatType = Literal[
    "hook",
    "promise",
    "stakes",
    "open_loop",
    "proof",
    "re_hook",
    "mini_payoff",
    "payoff",
    "cta",
]


class TranscriptSegment(BaseModel):
    start: float = Field(ge=0)
    duration: float = Field(default=0, ge=0)
    text: str = Field(min_length=1)


class VideoMetadata(BaseModel):
    video_id: str
    title: str = ""
    channel: str = ""
    duration_seconds: int | None = Field(default=None, ge=0)
    url: str


class NarrativeBeat(BaseModel):
    type: BeatType
    start: float = Field(ge=0)
    end: float = Field(ge=0)
    evidence: str = Field(min_length=1)
    explanation: str = Field(min_length=1)

    @model_validator(mode="after")
    def valid_interval(self) -> "NarrativeBeat":
        if self.end < self.start:
            raise ValueError("Beat end must not precede its start")
        return self


class AnalysisResult(BaseModel):
    metadata: VideoMetadata
    language: str
    summary: str = Field(min_length=1)
    key_points: list[str] = Field(default_factory=list)
    claims: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)
    quotes: list[str] = Field(default_factory=list)
    calls_to_action: list[str] = Field(default_factory=list)
    narrative_beats: list[NarrativeBeat] = Field(default_factory=list)
    reusable_template: list[str] = Field(min_length=1)
    transcript_source: Literal["captions", "whisper"] = "captions"
    model: str


class AnalyzeRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2048)
    language: str = Field(default="zh", pattern=r"^[a-zA-Z]{2,3}(-[a-zA-Z0-9]{2,8})*$")
    model: str = Field(default="llama3.1:8b", min_length=1, max_length=200)
    whisper_model: str = Field(default="small", min_length=1, max_length=100)
