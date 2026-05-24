from __future__ import annotations

import os
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable

from utils.json_helpers import parse_json_object
from utils.schemas import AudioPayload, TranscriptPayload, TranscriptSegment


CHUNK_DURATION = int(os.getenv("AUDIO_CHUNK_SECONDS", "20"))

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


def _split_into_chunks(audio_path: Path, chunk_duration: int, job_dir: Path) -> list[tuple[Path, float]]:
    """Split WAV into MP3 chunks — ~8x smaller than WAV, much faster to upload."""
    chunks_dir = job_dir / "chunks"
    chunks_dir.mkdir(exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(audio_path),
            "-f", "segment", "-segment_time", str(chunk_duration),
            "-c:a", "libmp3lame", "-b:a", "32k",
            "-reset_timestamps", "1",
            str(chunks_dir / "chunk_%03d.mp3"),
        ],
        capture_output=True,
        check=True,
    )
    paths = sorted(chunks_dir.glob("chunk_*.mp3"))
    return [(path, i * chunk_duration) for i, path in enumerate(paths)]


def _gemini_transcribe_file(audio_path: str, job_label: str) -> dict:
    from google import genai
    from google.genai import types

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY is required for Gemini transcription.")

    mime_type = "audio/mp3" if audio_path.endswith(".mp3") else "audio/wav"

    client = genai.Client(api_key=api_key)
    audio_file = client.files.upload(
        file=audio_path,
        config=types.UploadFileConfig(mime_type=mime_type, display_name=job_label),
    )
    while audio_file.state.name == "PROCESSING":
        time.sleep(0.5)
        audio_file = client.files.get(name=audio_file.name)
    if audio_file.state.name == "FAILED":
        raise RuntimeError(f"Gemini file upload failed: {audio_file.state}")

    model_name = os.getenv("GEMINI_TRANSCRIBE_MODEL", "gemini-2.5-flash")
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=[audio_file, TRANSCRIPTION_PROMPT],
            config=types.GenerateContentConfig(temperature=0.1, response_mime_type="application/json"),
        )
        return parse_json_object(response.text)
    finally:
        client.files.delete(name=audio_file.name)


def _translate_chunk(job_id: str, chunk_idx: int, segments: list[dict], detected_language: str, target_languages: list[str]) -> dict[str, list[dict]]:
    from agents import agent3_translate
    payload = {
        "job_id": f"{job_id}_chunk{chunk_idx}",
        "segments": segments,
        "full_text": " ".join(s["text"] for s in segments),
        "detected_language": detected_language,
        "word_count": sum(len(s["text"].split()) for s in segments),
        "target_languages": target_languages,
    }
    result = agent3_translate.run(payload)
    return result.get("subtitles", {})


def _transcribe_chunks_parallel(
    audio: AudioPayload,
    on_partial: Callable[[dict], None] | None = None,
) -> dict:
    job_dir = Path(audio.audio_path).parent
    chunks = _split_into_chunks(Path(audio.audio_path), CHUNK_DURATION, job_dir)
    target_languages = audio.target_languages or []

    if len(chunks) == 1:
        raw = _gemini_transcribe_file(audio.audio_path, f"interview_{audio.job_id}")
        subtitles = _translate_chunk(audio.job_id, 0, raw.get("segments", []), raw.get("detected_language", "en"), target_languages)
        if on_partial:
            on_partial({"transcript": raw, "subtitles": subtitles})
        return raw

    completed_segs: dict[int, list[dict]] = {}
    completed_subs: dict[int, dict[str, list[dict]]] = {}
    detected_language = "en"
    lock = threading.Lock()

    def _emit_partial() -> None:
        all_segs: list[dict] = []
        merged_subs: dict[str, list[dict]] = {}
        for i in sorted(completed_segs.keys()):
            all_segs.extend(completed_segs[i])
            for lang_code, lang_segs in completed_subs.get(i, {}).items():
                merged_subs.setdefault(lang_code, []).extend(lang_segs)
        on_partial({
            "transcript": {
                "detected_language": detected_language,
                "segments": all_segs,
                "full_text": " ".join(s["text"] for s in all_segs),
            },
            "subtitles": merged_subs,
        })

    def process_chunk(idx: int, chunk_path: Path, offset: float) -> tuple[int, list[dict], dict[str, list[dict]], str]:
        raw = _gemini_transcribe_file(str(chunk_path), f"interview_{audio.job_id}_chunk{idx}")
        lang = raw.get("detected_language", "en")
        segments = []
        for seg in raw.get("segments", []):
            seg = dict(seg)
            seg["start"] = round(seg["start"] + offset, 3)
            seg["end"] = round(seg["end"] + offset, 3)
            segments.append(seg)

        # Translate all languages before emitting so all are available together
        subtitles = _translate_chunk(audio.job_id, idx, segments, lang, target_languages)

        with lock:
            completed_segs[idx] = segments
            completed_subs[idx] = subtitles
            if on_partial:
                _emit_partial()

        return idx, segments, subtitles, lang

    with ThreadPoolExecutor(max_workers=len(chunks)) as executor:
        futures = {
            executor.submit(process_chunk, idx, path, offset): idx
            for idx, (path, offset) in enumerate(chunks)
        }
        for future in as_completed(futures):
            idx, segments, subtitles, lang = future.result()
            with lock:
                detected_language = lang

    all_segments: list[dict] = []
    for i in range(len(chunks)):
        all_segments.extend(completed_segs.get(i, []))
    for i, seg in enumerate(all_segments):
        seg["id"] = i

    return {
        "detected_language": detected_language,
        "segments": all_segments,
        "full_text": " ".join(seg["text"] for seg in all_segments),
    }


def _transcribe_with_gemini(audio: AudioPayload) -> dict:
    return _gemini_transcribe_file(audio.audio_path, f"interview_{audio.job_id}")


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
        segments.append({
            "id": index,
            "start": float(segment.start),
            "end": float(segment.end),
            "speaker": "AUDIO",
            "text": text,
            "confidence": 0.9,
        })

    return {
        "detected_language": getattr(info, "language", None) or language or "en",
        "segments": segments,
        "full_text": " ".join(segment["text"] for segment in segments),
    }


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


def run(audio_payload: dict, on_partial: Callable[[dict], None] | None = None) -> dict:
    audio = AudioPayload.model_validate(audio_payload)
    if not Path(audio.audio_path).exists():
        raise FileNotFoundError(f"Audio file not found: {audio.audio_path}")

    if os.getenv("MOCK_AI", "").lower() in {"1", "true", "yes"}:
        result = _mock_transcript(audio)
        if on_partial:
            on_partial({"transcript": result, "subtitles": {}})
    elif os.getenv("TRANSCRIBE_PROVIDER", "auto").lower() in {"local", "local_whisper", "whisper"}:
        result = _transcribe_with_local_whisper(audio)
        if on_partial:
            on_partial({"transcript": result, "subtitles": {}})
    elif os.getenv("GOOGLE_API_KEY"):
        result = _transcribe_chunks_parallel(audio, on_partial=on_partial)
    else:
        result = _transcribe_with_local_whisper(audio)
        if on_partial:
            on_partial({"transcript": result, "subtitles": {}})

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
