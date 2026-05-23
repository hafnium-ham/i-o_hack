from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from utils.gmi_client import get_gmi_client
from utils.json_helpers import parse_json_object
from utils.schemas import SubtitlePayload, TranscriptPayload


LANGUAGE_NAMES = {
    "en": "English",
    "es": "Spanish",
    "pt": "Portuguese",
    "fr": "French",
    "ar": "Arabic",
    "ja": "Japanese",
    "de": "German",
}

TRANSLATE_SYSTEM = """You are a professional sports broadcast subtitle translator.
Translate each segment's text into {target_language}.
Return only valid JSON: either an array of segments or an object with a "segments" array.
Preserve id, start, and end exactly. Do not add, remove, or reorder segments."""


def _source_subtitles(transcript: TranscriptPayload) -> list[dict]:
    return [
        {"id": segment.id, "start": segment.start, "end": segment.end, "text": segment.text}
        for segment in transcript.segments
    ]


def _mock_translate(segments: list[dict], target_lang: str) -> list[dict]:
    lang_name = LANGUAGE_NAMES.get(target_lang, target_lang)
    return [{**segment, "text": f"[{lang_name}] {segment['text']}"} for segment in segments]


def translate_language(segments: list[dict], target_lang: str) -> tuple[str, list[dict]]:
    if os.getenv("MOCK_AI", "").lower() in {"1", "true", "yes"}:
        return target_lang, _mock_translate(segments, target_lang)

    client = get_gmi_client()
    model = os.getenv("GMI_TRANSLATION_MODEL", "meta-llama/Llama-3.3-70B-Instruct")
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": TRANSLATE_SYSTEM.format(target_language=LANGUAGE_NAMES.get(target_lang, target_lang))},
            {"role": "user", "content": json.dumps(segments, ensure_ascii=False)},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
        max_tokens=4096,
    )
    parsed = parse_json_object(response.choices[0].message.content)
    if isinstance(parsed, dict):
        parsed = parsed.get("segments") or next(iter(parsed.values()))
    return target_lang, parsed


def run(transcript_payload: dict) -> dict:
    transcript = TranscriptPayload.model_validate(transcript_payload)
    source_segments = _source_subtitles(transcript)
    subtitles: dict[str, list[dict]] = {transcript.detected_language: source_segments}
    if transcript.detected_language == "en":
        subtitles.setdefault("en", source_segments)

    langs_to_translate = [
        lang for lang in transcript.target_languages
        if lang != transcript.detected_language and lang not in subtitles
    ]

    if langs_to_translate:
        with ThreadPoolExecutor(max_workers=min(len(langs_to_translate), 6)) as executor:
            futures = {executor.submit(translate_language, source_segments, lang): lang for lang in langs_to_translate}
            for future in as_completed(futures):
                lang = futures[future]
                try:
                    lang_code, translated = future.result()
                    subtitles[lang_code] = translated
                except Exception as exc:
                    subtitles[lang] = [{"id": s["id"], "start": s["start"], "end": s["end"], "text": s["text"]} for s in source_segments]
                    subtitles[f"{lang}_error"] = [{"id": 0, "start": 0.0, "end": 0.0, "text": str(exc)}]

    return SubtitlePayload(job_id=transcript.job_id, subtitles=subtitles).model_dump()
