from __future__ import annotations

import os
import time
from pathlib import Path

from utils.json_helpers import parse_json_object
from utils.schemas import AudioPayload, TranscriptPayload, TranscriptSegment


TRANSCRIPTION_PROMPT = """
You are a professional sports broadcast transcription service.

Transcribe the audio in full. Identify each speaker as REPORTER, PLAYER, or OTHER.
Return only valid JSON with this shape:
{
  "detected_language": "en",
  "segments": [
    {"id": 0, "start": 0.0, "end": 4.2, "speaker": "REPORTER", "text": "...", "confidence": 0.95}
  ],
  "full_text": "complete transcript joined together"
}
Keep timestamps as float seconds and include filler words.
"""


def _transcribe_with_local_whisper(audio: AudioPayload) -> dict:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError("Install 'faster-whisper' to use local transcription.") from exc

    model_name = os.getenv("LOCAL_WHISPER_MODEL", "tiny")
    device = os.getenv("LOCAL_WHISPER_DEVICE", "auto")
    compute_type = os.getenv("LOCAL_WHISPER_COMPUTE_TYPE", "int8")
    language = os.getenv("LOCAL_WHISPER_LANGUAGE") or None

    model = WhisperModel(model_name, device=device, compute_type=compute_type)
    segments_iter, info = model.transcribe(
        audio.audio_path,
        beam_size=int(os.getenv("LOCAL_WHISPER_BEAM_SIZE", "1")),
        vad_filter=os.getenv("LOCAL_WHISPER_VAD", "true").lower() in {"1", "true", "yes"},
        language=language,
    )

    segments = []
    for index, segment in enumerate(segments_iter):
        text = segment.text.strip()
        if not text:
            continue
        segments.append(
            {
                "id": index,
                "start": float(segment.start),
                "end": float(segment.end),
                "speaker": "AUDIO",
                "text": text,
                "confidence": 0.9,
            }
        )

    return {
        "detected_language": getattr(info, "language", None) or language or "en",
        "segments": segments,
        "full_text": " ".join(segment["text"] for segment in segments),
    }


def _transcribe_with_gemini(audio: AudioPayload) -> dict:
    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise RuntimeError("Install 'google-genai' to use Gemini transcription.") from exc

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY is required for Gemini transcription.")

    client = genai.Client(api_key=api_key)

    audio_file = client.files.upload(
        file=audio.audio_path,
        config=types.UploadFileConfig(
            mime_type="audio/wav",
            display_name=f"interview_{audio.job_id}",
        ),
    )

    while audio_file.state.name == "PROCESSING":
        time.sleep(2)
        audio_file = client.files.get(name=audio_file.name)

    if audio_file.state.name == "FAILED":
        raise RuntimeError(f"Gemini file upload failed: {audio_file.state}")

    model_name = os.getenv("GEMINI_TRANSCRIBE_MODEL", "gemini-2.5-flash")
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=[audio_file, TRANSCRIPTION_PROMPT],
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
            ),
        )
        return parse_json_object(response.text)
    finally:
        client.files.delete(name=audio_file.name)


def _mock_transcript(audio: AudioPayload) -> dict:
    text = (
        "I scored three goals tonight and I am proud of the team. "
        "Lionel Messi and Kylian Mbappe pushed the tempo all match."
    )
    return {
        "detected_language": "en",
        "segments": [
            {
                "id": 0,
                "start": 0.0,
                "end": min(audio.duration_seconds, 6.0),
                "speaker": "PLAYER",
                "text": text,
                "confidence": 0.8,
            }
        ],
        "full_text": text,
    }


def run(audio_payload: dict) -> dict:
    audio = AudioPayload.model_validate(audio_payload)
    if not Path(audio.audio_path).exists():
        raise FileNotFoundError(f"Audio file not found: {audio.audio_path}")

    if os.getenv("MOCK_AI", "").lower() in {"1", "true", "yes"}:
        result = _mock_transcript(audio)
    elif os.getenv("TRANSCRIBE_PROVIDER", "auto").lower() in {"local", "local_whisper", "whisper"}:
        result = _transcribe_with_local_whisper(audio)
    elif os.getenv("GOOGLE_API_KEY"):
        result = _transcribe_with_gemini(audio)
    else:
        result = _transcribe_with_local_whisper(audio)

    segments = [TranscriptSegment.model_validate(seg) for seg in result.get("segments", [])]
    full_text = result.get("full_text") or " ".join(seg.text for seg in segments)
    payload = TranscriptPayload(
        job_id=audio.job_id,
        segments=segments,
        full_text=full_text,
        detected_language=result.get("detected_language", "en"),
        word_count=sum(len(seg.text.split()) for seg in segments),
        target_languages=audio.target_languages,
    )
    return payload.model_dump()
