from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


SUPPORTED_LANGUAGES = {"en", "es", "pt", "fr", "ar", "ja", "de"}


class RawInput(BaseModel):
    source_type: Literal["youtube_url", "file_path"]
    source_value: str = Field(min_length=1)
    target_languages: list[str] = Field(default_factory=lambda: ["es", "pt", "fr", "ar", "ja"])
    job_id: str | None = None

    @field_validator("target_languages")
    @classmethod
    def validate_languages(cls, value: list[str]) -> list[str]:
        invalid = sorted(set(value) - SUPPORTED_LANGUAGES)
        if invalid:
            raise ValueError(f"Unsupported target language(s): {', '.join(invalid)}")
        return value


class AudioPayload(BaseModel):
    job_id: str
    audio_path: str
    duration_seconds: float
    source_title: str
    source_url: str | None = None
    target_languages: list[str] = Field(default_factory=list)


class TranscriptSegment(BaseModel):
    id: int
    start: float
    end: float
    speaker: str
    text: str
    confidence: float = 0.9


class TranscriptPayload(BaseModel):
    job_id: str
    segments: list[TranscriptSegment]
    full_text: str
    detected_language: str = "en"
    word_count: int = 0
    target_languages: list[str] = Field(default_factory=list)


class SubtitleSegment(BaseModel):
    id: int
    start: float
    end: float
    text: str


class SubtitlePayload(BaseModel):
    job_id: str
    subtitles: dict[str, list[SubtitleSegment]]


class StatEvent(BaseModel):
    segment_id: int
    timestamp_start: float
    timestamp_end: float
    player_name: str
    stat_category: str
    mentioned_value: str = ""
    player_card: dict[str, Any] | None = None
    highlight_text: str
    gemini_extraction: dict[str, Any] | None = None


class AnalysisPayload(BaseModel):
    job_id: str
    summary_bullets: list[str]
    overall_sentiment: str
    speaker_sentiment: dict[str, str]
    tone_timeline: list[dict[str, Any]]


class FinalOutput(BaseModel):
    job_id: str
    source_title: str | None = None
    source_url: str | None = None
    duration_seconds: float | None = None
    transcript: dict[str, Any]
    subtitles: dict[str, Any]
    stat_events: list[dict[str, Any]]
    analysis: dict[str, Any]
    processing_time_seconds: float
    processed_at: float

