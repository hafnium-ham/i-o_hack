from __future__ import annotations

import os

from utils.gmi_client import get_gmi_client
from utils.json_helpers import parse_json_object
from utils.schemas import AnalysisPayload, TranscriptPayload


ANALYSIS_SYSTEM = """You are an expert sports journalist and broadcast analyst.
Return only valid JSON with summary_bullets, overall_sentiment, speaker_sentiment, and tone_timeline.
summary_bullets must contain 3-5 concise points."""


def _mock_analysis(transcript: TranscriptPayload) -> dict:
    speakers = sorted({segment.speaker for segment in transcript.segments})
    return {
        "summary_bullets": [
            "Player highlighted scoring impact and team execution",
            "Interview tone stayed confident and composed",
            "Named stars were linked to match momentum",
        ],
        "overall_sentiment": "confident",
        "speaker_sentiment": {speaker: ("confident" if speaker == "PLAYER" else "neutral") for speaker in speakers},
        "tone_timeline": [{"segment_id": segment.id, "tone": "confident" if segment.speaker == "PLAYER" else "neutral"} for segment in transcript.segments],
    }


def _normalize_analysis(result: object, transcript: TranscriptPayload) -> dict:
    speakers = sorted({segment.speaker for segment in transcript.segments}) or ["AUDIO"]
    data = result if isinstance(result, dict) else {}

    summary = data.get("summary_bullets")
    if not isinstance(summary, list):
        summary = ["Interview processed and prepared for translated playback"]
    summary = [str(item) for item in summary if str(item).strip()][:5] or [
        "Interview processed and prepared for translated playback"
    ]

    overall = data.get("overall_sentiment", "neutral")
    if not isinstance(overall, str):
        overall = "neutral"

    speaker_sentiment = data.get("speaker_sentiment")
    if isinstance(speaker_sentiment, dict):
        speaker_sentiment = {str(key): str(value) for key, value in speaker_sentiment.items()}
    else:
        speaker_sentiment = {speaker: str(speaker_sentiment or overall) for speaker in speakers}

    tone_timeline = data.get("tone_timeline")
    if not isinstance(tone_timeline, list):
        tone_timeline = [{"segment_id": segment.id, "tone": overall} for segment in transcript.segments]
    else:
        tone_timeline = [
            item if isinstance(item, dict) else {"segment_id": index, "tone": str(item)}
            for index, item in enumerate(tone_timeline)
        ]

    return {
        "summary_bullets": summary,
        "overall_sentiment": overall,
        "speaker_sentiment": speaker_sentiment,
        "tone_timeline": tone_timeline,
    }


def run(transcript_payload: dict) -> dict:
    transcript = TranscriptPayload.model_validate(transcript_payload)

    if os.getenv("MOCK_AI", "").lower() in {"1", "true", "yes"}:
        result = _mock_analysis(transcript)
    else:
        client = get_gmi_client()
        model = os.getenv("GMI_ANALYSIS_MODEL", "meta-llama/Llama-3.3-70B-Instruct")
        transcript_text = "\n".join(
            f"[{segment.speaker}, segment {segment.id}]: {segment.text}"
            for segment in transcript.segments
        )
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": ANALYSIS_SYSTEM},
                {"role": "user", "content": f"Analyze this interview:\n\n{transcript_text}"},
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
            max_tokens=2048,
        )
        result = parse_json_object(response.choices[0].message.content)

    return AnalysisPayload(job_id=transcript.job_id, **_normalize_analysis(result, transcript)).model_dump()
