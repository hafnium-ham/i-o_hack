# ⚽ World Cup AI Broadcast Assistant — Backend Pipeline Plan

**Hackathon:** GDG Newport Beach × RocketRide × GMI Cloud, San Francisco  
**Stack:** Google AI Studio (Gemini) · RocketRide AIDE · GMI Cloud (NVIDIA H100/H200)  
**Goal:** A 5-agent pipeline that ingests post-match interview video/audio and outputs structured
transcription, multi-language subtitles, player stat overlays, an interview summary, and a
sentiment profile — all orchestrated through RocketRide and powered by GMI Cloud inference.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Tech Stack & Credentials](#2-tech-stack--credentials)
3. [Data Contracts — Schemas Between Agents](#3-data-contracts--schemas-between-agents)
4. [Agent 1 — Ingestion & Audio Extraction](#4-agent-1--ingestion--audio-extraction)
5. [Agent 2 — Transcription & Speaker Diarization](#5-agent-2--transcription--speaker-diarization)
6. [Agent 3 — Translation Engine](#6-agent-3--translation-engine)
7. [Agent 4 — Stat Extraction & Player Intelligence](#7-agent-4--stat-extraction--player-intelligence)
8. [Agent 5 — Summary & Sentiment Analysis](#8-agent-5--summary--sentiment-analysis)
9. [RocketRide Pipeline Definition (.pipe)](#9-rocketride-pipeline-definition-pipe)
10. [GMI Cloud Inference Integration](#10-gmi-cloud-inference-integration)
11. [Player Stats Database](#11-player-stats-database)
12. [FastAPI Wrapper (Frontend Bridge)](#12-fastapi-wrapper-frontend-bridge)
13. [Project File Structure](#13-project-file-structure)
14. [Environment Variables](#14-environment-variables)
15. [Build Order & Time Estimates](#15-build-order--time-estimates)
16. [Testing Strategy](#16-testing-strategy)
17. [Demo Payload (Sample Inputs & Expected Outputs)](#17-demo-payload-sample-inputs--expected-outputs)
18. [Phase 2 Roadmap (Post-Hackathon)](#18-phase-2-roadmap-post-hackathon)

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        INPUT LAYER                                  │
│   YouTube URL  ─── or ───  File Upload (.mp4 / .mp3 / .wav)         │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│              ROCKETRIDE PIPELINE ENGINE (C++ runtime)               │
│                                                                     │
│  ┌───────────┐    ┌───────────┐    ┌───────────┐    ┌───────────┐  │
│  │ AGENT 1   │───▶│ AGENT 2   │───▶│ AGENT 3   │───▶│ AGENT 4   │  │
│  │ Ingest &  │    │Transcribe │    │ Translate │    │  Stats    │  │
│  │ Extract   │    │ + Diarize │    │ Subtitles │    │ Overlay   │  │
│  └───────────┘    └───────────┘    └───────────┘    └─────┬─────┘  │
│                                                           │        │
│                                                     ┌─────▼─────┐  │
│                                                     │ AGENT 5   │  │
│                                                     │ Summary + │  │
│                                                     │ Sentiment │  │
│                                                     └───────────┘  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         OUTPUT PAYLOAD (JSON)                       │
│  transcript · subtitles[lang] · stat_events · summary · sentiment   │
└─────────────────────────────────────────────────────────────────────┘
```

### Key Architectural Decisions

- **RocketRide** orchestrates all agents as a `.pipe` JSON graph. Each agent is either a
  native RocketRide node (Audio, LLM, Text) or a Python Tool node wrapping custom logic.
- **GMI Cloud** (OpenAI-compatible API at `https://api.gmi-serving.com/v1`) handles all
  heavy LLM inference calls. Gemini handles multimodal audio processing via Google AI Studio.
- **Data flows as JSON** between lanes. Every agent consumes and emits a typed JSON payload
  so any node can be hot-swapped without touching adjacent agents.
- **The player stats DB is a flat JSON file** loaded at startup — zero DB overhead during
  the hackathon, trivially upgradeable to Postgres or Pinecone later.

---

## 2. Tech Stack & Credentials

| Service             | Purpose                                                          | Auth             |
| ------------------- | ---------------------------------------------------------------- | ---------------- |
| Google AI Studio    | Gemini 2.0 Flash — audio transcription, multimodal understanding | `GOOGLE_API_KEY` |
| GMI Cloud Inference | LLM calls for translation, extraction, summary, sentiment        | `GMI_API_KEY`    |
| RocketRide AIDE     | Pipeline orchestration, node graph, runtime                      | Local / Docker   |
| `yt-dlp` (Python)   | YouTube URL → audio extraction                                   | None             |
| `ffmpeg`            | Audio format normalization                                       | System binary    |
| FastAPI             | REST wrapper exposing pipeline to any frontend                   | None             |

### GMI Cloud Base URL

```
https://api.gmi-serving.com/v1
```

This is fully OpenAI-compatible — use any `openai` Python SDK client by just setting
`base_url` and `api_key`. Every LLM call below uses this pattern.

### Recommended GMI Models

| Task                               | Model                                 | Why                                     |
| ---------------------------------- | ------------------------------------- | --------------------------------------- |
| Translation                        | `meta-llama/Llama-3.3-70B-Instruct`   | Fast, multilingual, instruction-tuned   |
| Stat extraction (function calling) | `deepseek-ai/DeepSeek-R1`             | Strong reasoning, function call support |
| Summary + sentiment                | `meta-llama/Llama-3.3-70B-Instruct`   | Reliable structured output              |
| Transcription                      | Gemini 2.0 Flash via Google AI Studio | Native audio modality                   |

---

## 3. Data Contracts — Schemas Between Agents

Every agent speaks JSON. Define these TypedDicts / Pydantic models in `schemas.py`.

### `RawInput`

```json
{
  "source_type": "youtube_url | file_path",
  "source_value": "https://www.youtube.com/watch?v=... | /tmp/interview.mp4",
  "target_languages": ["es", "pt", "fr", "ar", "ja"],
  "job_id": "uuid4-string"
}
```

### `AudioPayload` (Agent 1 → Agent 2)

```json
{
  "job_id": "...",
  "audio_path": "/tmp/jobs/<job_id>/audio.wav",
  "duration_seconds": 312,
  "source_title": "Mbappe Post-Match Press Conference",
  "source_url": "https://..."
}
```

### `TranscriptPayload` (Agent 2 → Agents 3, 4, 5)

```json
{
  "job_id": "...",
  "segments": [
    {
      "id": 0,
      "start": 0.0,
      "end": 4.2,
      "speaker": "REPORTER",
      "text": "Kylian, how do you feel about the hat-trick tonight?",
      "confidence": 0.97
    },
    {
      "id": 1,
      "start": 4.5,
      "end": 9.1,
      "speaker": "PLAYER",
      "text": "I scored 3 goals and I'm really proud of the team.",
      "confidence": 0.95
    }
  ],
  "full_text": "...",
  "detected_language": "en",
  "word_count": 412
}
```

### `SubtitlePayload` (Agent 3 → Output)

```json
{
  "job_id": "...",
  "subtitles": {
    "en": [{ "id": 0, "start": 0.0, "end": 4.2, "text": "..." }],
    "es": [{ "id": 0, "start": 0.0, "end": 4.2, "text": "..." }],
    "pt": [{ "id": 0, "start": 0.0, "end": 4.2, "text": "..." }]
  }
}
```

### `StatEvent` (one entry per detected stat mention)

```json
{
  "segment_id": 1,
  "timestamp_start": 4.5,
  "timestamp_end": 9.1,
  "player_name": "Kylian Mbappé",
  "stat_category": "goals",
  "mentioned_value": "3",
  "player_card": {
    "name": "Kylian Mbappé",
    "club": "Real Madrid",
    "nation": "France",
    "position": "FW",
    "tournament_goals": 5,
    "tournament_assists": 2,
    "caps": 87,
    "goals_international": 49
  },
  "highlight_text": "I scored 3 goals"
}
```

### `AnalysisPayload` (Agent 5 → Output)

```json
{
  "job_id": "...",
  "summary_bullets": [
    "Scored hat-trick, credits team defensive shape",
    "Confirmed minor knock, expects to train Thursday",
    "Expressed confidence ahead of quarterfinal"
  ],
  "overall_sentiment": "confident",
  "speaker_sentiment": {
    "PLAYER": "confident",
    "REPORTER": "neutral"
  },
  "tone_timeline": [
    { "segment_id": 0, "tone": "neutral" },
    { "segment_id": 1, "tone": "proud" }
  ]
}
```

### `FinalOutput` (complete pipeline result)

```json
{
  "job_id": "...",
  "audio_payload": {...},
  "transcript": {...},
  "subtitles": {...},
  "stat_events": [...],
  "analysis": {...},
  "processing_time_seconds": 18.4
}
```

---

## 4. Agent 1 — Ingestion & Audio Extraction

**File:** `agents/agent1_ingest.py`  
**RocketRide Node Type:** Python Tool Node  
**Input:** `RawInput` JSON  
**Output:** `AudioPayload` JSON

### Responsibilities

1. Accept either a YouTube URL or a local file path
2. Download audio via `yt-dlp` (YouTube) or copy the file (local)
3. Normalize to mono 16kHz WAV using `ffmpeg` — Gemini's preferred audio format
4. Extract video title / metadata if YouTube source
5. Emit `AudioPayload`

### Code

```python
# agents/agent1_ingest.py
import subprocess
import uuid
import os
import json
from pathlib import Path

JOBS_DIR = Path("/tmp/jobs")

def run(raw_input: dict) -> dict:
    """
    RocketRide Python Tool node entrypoint.
    Receives RawInput, returns AudioPayload.
    """
    job_id = raw_input.get("job_id", str(uuid.uuid4()))
    job_dir = JOBS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    source_type = raw_input["source_type"]
    source_value = raw_input["source_value"]
    title = "Unknown Interview"

    if source_type == "youtube_url":
        raw_audio = job_dir / "raw_audio"
        # yt-dlp: download best audio only
        result = subprocess.run([
            "yt-dlp",
            "--extract-audio",
            "--audio-format", "wav",
            "--audio-quality", "0",
            "--output", str(raw_audio) + ".%(ext)s",
            "--print", "title",         # capture title
            source_value
        ], capture_output=True, text=True, check=True)
        title = result.stdout.strip().split("\n")[0] or "YouTube Interview"
        raw_path = next(job_dir.glob("raw_audio.*"))

    elif source_type == "file_path":
        raw_path = Path(source_value)
        title = raw_path.stem
    else:
        raise ValueError(f"Unknown source_type: {source_type}")

    # Normalize: mono, 16kHz, WAV PCM
    normalized_path = job_dir / "audio.wav"
    subprocess.run([
        "ffmpeg", "-y",
        "-i", str(raw_path),
        "-ar", "16000",          # 16kHz sample rate
        "-ac", "1",              # mono
        "-c:a", "pcm_s16le",    # 16-bit PCM
        str(normalized_path)
    ], capture_output=True, check=True)

    # Get duration
    probe = subprocess.run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json", str(normalized_path)
    ], capture_output=True, text=True, check=True)
    duration = float(json.loads(probe.stdout)["format"]["duration"])

    return {
        "job_id": job_id,
        "audio_path": str(normalized_path),
        "duration_seconds": duration,
        "source_title": title,
        "source_url": source_value if source_type == "youtube_url" else None
    }
```

### Dependencies

```
yt-dlp>=2024.1.0
ffmpeg-python>=0.2.0
```

> **Note:** `ffmpeg` and `ffprobe` must be installed as system binaries
> (`apt install ffmpeg` or `brew install ffmpeg`).

---

## 5. Agent 2 — Transcription & Speaker Diarization

**File:** `agents/agent2_transcribe.py`  
**RocketRide Node Type:** RocketRide Audio Node → Google LLM Node (chained)  
**Input:** `AudioPayload`  
**Output:** `TranscriptPayload`

### Strategy

Gemini 2.0 Flash accepts audio files natively via the Files API. We upload the normalized
WAV, send a structured prompt requesting speaker-labeled JSON output, and parse the response.
This gives us transcription + basic diarization in a single API call — no separate
diarization service needed.

### Code

````python
# agents/agent2_transcribe.py
import google.generativeai as genai
import json
import os
import time
from pathlib import Path

genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

TRANSCRIPTION_PROMPT = """
You are a professional sports broadcast transcription service.

Transcribe the audio file in full. Identify and label each speaker as either:
- REPORTER (any journalist or moderator asking questions)
- PLAYER (the athlete being interviewed)
- OTHER (translator, official, etc.)

Return ONLY valid JSON with this exact structure — no markdown, no commentary:
{
  "detected_language": "en",
  "segments": [
    {
      "id": 0,
      "start": 0.0,
      "end": 4.2,
      "speaker": "REPORTER",
      "text": "exact text here",
      "confidence": 0.95
    }
  ],
  "full_text": "complete transcript joined together"
}

Rules:
- Split on every speaker change and every natural pause longer than 1.5 seconds
- Include all filler words (um, uh) — do not clean up
- Timestamps must be float seconds from start of audio
- confidence is your certainty estimate 0.0-1.0
- detected_language is ISO 639-1 code of the dominant language spoken
"""

def run(audio_payload: dict) -> dict:
    audio_path = audio_payload["audio_path"]
    job_id = audio_payload["job_id"]

    # Upload audio to Gemini Files API
    print(f"[Agent 2] Uploading audio: {audio_path}")
    audio_file = genai.upload_file(
        path=audio_path,
        mime_type="audio/wav",
        display_name=f"interview_{job_id}"
    )

    # Wait for file to be ACTIVE
    while audio_file.state.name == "PROCESSING":
        time.sleep(2)
        audio_file = genai.get_file(audio_file.name)

    if audio_file.state.name == "FAILED":
        raise RuntimeError(f"Gemini file upload failed: {audio_file.state}")

    # Run transcription
    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(
        [audio_file, TRANSCRIPTION_PROMPT],
        generation_config=genai.GenerationConfig(
            temperature=0.1,    # low temp for accuracy
            response_mime_type="application/json"
        )
    )

    raw = response.text.strip()
    # Strip any accidental markdown fences
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    result = json.loads(raw)
    result["job_id"] = job_id
    result["word_count"] = sum(
        len(seg["text"].split()) for seg in result["segments"]
    )

    # Clean up uploaded file
    genai.delete_file(audio_file.name)

    print(f"[Agent 2] Transcribed {result['word_count']} words, "
          f"{len(result['segments'])} segments")
    return result
````

### Fallback: Whisper via GMI Cloud

If Gemini audio upload is flaky during the hackathon, fall back to Whisper large-v3
deployed on GMI Cloud:

```python
# fallback inside agent2_transcribe.py
import openai

def transcribe_whisper_fallback(audio_path: str) -> dict:
    client = openai.OpenAI(
        base_url="https://api.gmi-serving.com/v1",
        api_key=os.environ["GMI_API_KEY"]
    )
    with open(audio_path, "rb") as f:
        response = client.audio.transcriptions.create(
            model="openai/whisper-large-v3",
            file=f,
            response_format="verbose_json",
            timestamp_granularities=["segment"]
        )
    # Map whisper verbose_json format to our TranscriptPayload format
    segments = []
    for i, seg in enumerate(response.segments):
        segments.append({
            "id": i,
            "start": seg.start,
            "end": seg.end,
            "speaker": "UNKNOWN",   # Whisper doesn't diarize
            "text": seg.text.strip(),
            "confidence": 0.9
        })
    return {
        "detected_language": response.language,
        "segments": segments,
        "full_text": response.text,
        "word_count": len(response.text.split())
    }
```

---

## 6. Agent 3 — Translation Engine

**File:** `agents/agent3_translate.py`  
**RocketRide Node Type:** LLM Node (Google or GMI) — one parallel call per language  
**Input:** `TranscriptPayload`  
**Output:** `SubtitlePayload`

### Strategy

Translate each segment individually, preserving segment IDs and timestamps exactly.
We batch all segments into a single API call per language (not per segment) to minimize
latency. Use Llama 3.3 70B on GMI Cloud — it's fast and accurate for the 6 target languages.

### Supported Languages

| Code | Language   | World Cup Audience |
| ---- | ---------- | ------------------ |
| `en` | English    | Global default     |
| `es` | Spanish    | LATAM + Spain      |
| `pt` | Portuguese | Brazil             |
| `fr` | French     | France + Africa    |
| `ar` | Arabic     | MENA region        |
| `ja` | Japanese   | Japan              |
| `de` | German     | Germany            |

### Code

```python
# agents/agent3_translate.py
import openai
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

LANGUAGE_NAMES = {
    "es": "Spanish", "pt": "Portuguese", "fr": "French",
    "ar": "Arabic", "ja": "Japanese", "de": "German", "en": "English"
}

client = openai.OpenAI(
    base_url="https://api.gmi-serving.com/v1",
    api_key=os.environ["GMI_API_KEY"]
)

TRANSLATE_SYSTEM = """You are a professional sports broadcast subtitle translator.
You receive an array of subtitle segments in JSON and must translate the 'text' field
of each segment into {target_language}.

Rules:
- Return ONLY valid JSON — same array structure, same keys, only 'text' values changed
- Preserve sports terminology, player names, team names exactly as given
- Keep translations natural and broadcast-appropriate — not literal word-for-word
- Maintain the tone: excited comments stay excited, calm statements stay calm
- Do not add, remove, or reorder segments
"""

def translate_language(segments: list, target_lang: str) -> tuple[str, list]:
    """Translate all segments into one target language. Returns (lang_code, translated_segments)."""
    lang_name = LANGUAGE_NAMES.get(target_lang, target_lang)
    system = TRANSLATE_SYSTEM.format(target_language=lang_name)

    # Send all segments as one payload
    segments_json = json.dumps(segments, ensure_ascii=False)

    response = client.chat.completions.create(
        model="meta-llama/Llama-3.3-70B-Instruct",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": f"Translate these segments:\n{segments_json}"}
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
        max_tokens=4096
    )

    raw = response.choices[0].message.content
    translated = json.loads(raw)

    # Handle if model wrapped in a key
    if isinstance(translated, dict):
        translated = next(iter(translated.values()))

    return target_lang, translated

def run(transcript_payload: dict) -> dict:
    job_id = transcript_payload["job_id"]
    segments = transcript_payload["segments"]
    target_languages = transcript_payload.get(
        "target_languages",
        ["es", "pt", "fr", "ar", "ja"]
    )

    # Always include English (source or translated)
    result_subtitles = {
        "en": [{"id": s["id"], "start": s["start"], "end": s["end"], "text": s["text"]}
               for s in segments]
    }

    # Filter out source language from translation targets
    detected_lang = transcript_payload.get("detected_language", "en")
    langs_to_translate = [l for l in target_languages if l != detected_lang]

    print(f"[Agent 3] Translating into {langs_to_translate} (parallel)")

    # Run translations in parallel — one thread per language
    with ThreadPoolExecutor(max_workers=len(langs_to_translate)) as executor:
        futures = {
            executor.submit(translate_language, segments, lang): lang
            for lang in langs_to_translate
        }
        for future in as_completed(futures):
            try:
                lang_code, translated_segs = future.result()
                result_subtitles[lang_code] = translated_segs
                print(f"[Agent 3] ✓ {LANGUAGE_NAMES[lang_code]} complete")
            except Exception as e:
                lang = futures[future]
                print(f"[Agent 3] ✗ {lang} failed: {e}")
                # Graceful degradation: omit this language rather than crashing

    return {
        "job_id": job_id,
        "subtitles": result_subtitles
    }
```

---

## 7. Agent 4 — Stat Extraction & Player Intelligence

**File:** `agents/agent4_stats.py`  
**RocketRide Node Type:** LLM Node with Tool/Function Call → Python Tool Node (DB lookup)  
**Input:** `TranscriptPayload`  
**Output:** `List[StatEvent]`

### Strategy

This is the star of the demo. We use Gemini function calling to identify every mention of
a player name or a statistical reference in the transcript. For each hit, we look up the
player in our local stats JSON and construct a rich `StatEvent` card.

Two sub-steps:

1. **LLM extraction:** Gemini identifies player names + stat categories from transcript text
2. **DB lookup:** Python resolves the extracted name against `data/players.json` using
   fuzzy string matching

### Step 4a: LLM Extraction with Function Calling

```python
# agents/agent4_stats.py
import google.generativeai as genai
import json
import os
from rapidfuzz import process, fuzz
from pathlib import Path

genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

# Load player database once at module level
PLAYERS_DB_PATH = Path("data/players.json")
with open(PLAYERS_DB_PATH) as f:
    PLAYERS_DB = json.load(f)  # List of player dicts

# Build a fast lookup index: lowercase name → player dict
PLAYER_INDEX = {p["name"].lower(): p for p in PLAYERS_DB}
ALL_PLAYER_NAMES = list(PLAYER_INDEX.keys())

STAT_CATEGORIES = [
    "goals", "assists", "yellow_cards", "red_cards", "clean_sheets",
    "saves", "pass_accuracy", "distance_covered", "shots_on_target",
    "dribbles", "tackles", "minutes_played", "appearances"
]

# Gemini tool definition
EXTRACT_STATS_TOOL = genai.protos.Tool(
    function_declarations=[
        genai.protos.FunctionDeclaration(
            name="record_stat_mention",
            description="Record when a player name or stat category is mentioned in the transcript",
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    "segment_id": genai.protos.Schema(
                        type=genai.protos.Type.INTEGER,
                        description="The segment ID where the mention occurs"
                    ),
                    "player_name": genai.protos.Schema(
                        type=genai.protos.Type.STRING,
                        description="The full name or common name of the player mentioned"
                    ),
                    "stat_category": genai.protos.Schema(
                        type=genai.protos.Type.STRING,
                        description=f"Category of stat. One of: {', '.join(STAT_CATEGORIES)}, or 'general'"
                    ),
                    "mentioned_value": genai.protos.Schema(
                        type=genai.protos.Type.STRING,
                        description="The specific value mentioned (e.g. '3', 'twice', 'none')"
                    ),
                    "highlight_text": genai.protos.Schema(
                        type=genai.protos.Type.STRING,
                        description="The exact phrase in the transcript that triggered this"
                    )
                },
                required=["segment_id", "player_name", "stat_category", "highlight_text"]
            )
        )
    ]
)

EXTRACTION_PROMPT = """You are a football statistics analyst watching a post-match interview transcript.

Your job: identify every mention of:
1. A player's name (first name, last name, or nickname counts)
2. Any performance statistics (goals, assists, saves, tackles, etc.)
3. Any combination of the two

For EVERY such mention, call the record_stat_mention function once.
It is okay to call it multiple times — call it for EVERY mention you find.
If a sentence mentions both a player AND a stat, that's one call.
If multiple players are mentioned in one sentence, make separate calls for each.

Here is the transcript:
{transcript}"""

def fuzzy_lookup_player(name_mention: str) -> dict | None:
    """Fuzzy match a mentioned name against the players DB."""
    match, score, _ = process.extractOne(
        name_mention.lower(),
        ALL_PLAYER_NAMES,
        scorer=fuzz.token_sort_ratio
    )
    if score >= 70:  # 70% match threshold
        return PLAYER_INDEX[match]
    return None

def run(transcript_payload: dict) -> dict:
    job_id = transcript_payload["job_id"]
    segments = transcript_payload["segments"]

    # Build segment lookup for timestamp resolution
    seg_lookup = {s["id"]: s for s in segments}

    # Format transcript for the prompt
    transcript_text = "\n".join(
        f"[Segment {s['id']}, {s['start']:.1f}s-{s['end']:.1f}s, {s['speaker']}]: {s['text']}"
        for s in segments
    )

    prompt = EXTRACTION_PROMPT.format(transcript=transcript_text)

    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(
        prompt,
        tools=[EXTRACT_STATS_TOOL]
    )

    stat_events = []

    # Process function call responses
    for part in response.candidates[0].content.parts:
        if hasattr(part, "function_call") and part.function_call:
            fc = part.function_call
            if fc.name == "record_stat_mention":
                args = dict(fc.args)
                seg_id = int(args.get("segment_id", 0))
                seg = seg_lookup.get(seg_id, {})

                # Fuzzy-match player name to DB
                player_name = args.get("player_name", "")
                player_card = fuzzy_lookup_player(player_name)

                event = {
                    "segment_id": seg_id,
                    "timestamp_start": seg.get("start", 0.0),
                    "timestamp_end": seg.get("end", 0.0),
                    "player_name": player_name,
                    "stat_category": args.get("stat_category", "general"),
                    "mentioned_value": args.get("mentioned_value", ""),
                    "highlight_text": args.get("highlight_text", ""),
                    "player_card": player_card  # None if not in DB
                }
                stat_events.append(event)
                print(f"[Agent 4] Found: {player_name} → {args.get('stat_category')}")

    print(f"[Agent 4] Total stat events: {len(stat_events)}")
    return {
        "job_id": job_id,
        "stat_events": stat_events
    }
```

---

## 8. Agent 5 — Summary & Sentiment Analysis

**File:** `agents/agent5_analysis.py`  
**RocketRide Node Type:** LLM Node (GMI Cloud)  
**Input:** `TranscriptPayload`  
**Output:** `AnalysisPayload`

### Strategy

Single GMI Cloud call with structured JSON output mode. We ask for:

- 3–5 bullet summary of the interview's key points
- Overall speaker sentiment classification
- Per-segment tone label for the timeline

```python
# agents/agent5_analysis.py
import openai
import json
import os

client = openai.OpenAI(
    base_url="https://api.gmi-serving.com/v1",
    api_key=os.environ["GMI_API_KEY"]
)

ANALYSIS_SYSTEM = """You are an expert sports journalist and broadcast analyst.
You receive the transcript of a post-match football interview and must produce:

1. A summary_bullets array: 3-5 concise bullet points capturing the key things said
   (injuries, goals, tactics, emotions, team dynamics). Each bullet max 15 words.

2. overall_sentiment: one word describing the player's dominant mood:
   confident | relieved | frustrated | emotional | neutral | excited | defensive

3. speaker_sentiment: object mapping each speaker role to their sentiment word

4. tone_timeline: array with one entry per segment, each with segment_id and tone
   (one of: proud | frustrated | calm | excited | sad | anxious | neutral | evasive)

Return ONLY valid JSON. No markdown. Example structure:
{
  "summary_bullets": ["...", "..."],
  "overall_sentiment": "confident",
  "speaker_sentiment": {"PLAYER": "confident", "REPORTER": "neutral"},
  "tone_timeline": [{"segment_id": 0, "tone": "neutral"}]
}"""

def run(transcript_payload: dict) -> dict:
    job_id = transcript_payload["job_id"]
    segments = transcript_payload["segments"]

    transcript_text = "\n".join(
        f"[{s['speaker']}, segment {s['id']}]: {s['text']}"
        for s in segments
    )

    response = client.chat.completions.create(
        model="meta-llama/Llama-3.3-70B-Instruct",
        messages=[
            {"role": "system", "content": ANALYSIS_SYSTEM},
            {"role": "user", "content": f"Analyze this interview:\n\n{transcript_text}"}
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
        max_tokens=2048
    )

    raw = response.choices[0].message.content
    result = json.loads(raw)
    result["job_id"] = job_id

    print(f"[Agent 5] Sentiment: {result.get('overall_sentiment')}, "
          f"Summary: {len(result.get('summary_bullets', []))} bullets")
    return result
```

---

## 9. RocketRide Pipeline Definition (.pipe)

Pipelines in RocketRide are defined as JSON `.pipe` files. Each node has a type, configuration,
and named input/output lanes. Nodes connect by wiring output lanes to input lanes.

**File:** `pipeline/worldcup_broadcast.pipe`

```json
{
  "version": "1.0",
  "name": "worldcup_broadcast_pipeline",
  "description": "World Cup AI Broadcast Assistant — Post-match interview processing pipeline",
  "nodes": [
    {
      "id": "source",
      "type": "Source",
      "subtype": "Webhook",
      "config": {
        "port": 5565,
        "endpoint": "/process",
        "method": "POST"
      },
      "outputs": ["raw_input"]
    },
    {
      "id": "agent1_ingest",
      "type": "Tool",
      "subtype": "Python",
      "config": {
        "script": "agents/agent1_ingest.py",
        "function": "run"
      },
      "inputs": ["raw_input"],
      "outputs": ["audio_payload"]
    },
    {
      "id": "agent2_transcribe",
      "type": "Audio",
      "subtype": "Transcription",
      "config": {
        "provider": "google",
        "model": "gemini-2.0-flash",
        "script": "agents/agent2_transcribe.py",
        "function": "run"
      },
      "inputs": ["audio_payload"],
      "outputs": ["transcript_payload"]
    },
    {
      "id": "agent3_translate",
      "type": "Tool",
      "subtype": "Python",
      "config": {
        "script": "agents/agent3_translate.py",
        "function": "run"
      },
      "inputs": ["transcript_payload"],
      "outputs": ["subtitle_payload"]
    },
    {
      "id": "agent4_stats",
      "type": "Tool",
      "subtype": "Python",
      "config": {
        "script": "agents/agent4_stats.py",
        "function": "run"
      },
      "inputs": ["transcript_payload"],
      "outputs": ["stat_events_payload"]
    },
    {
      "id": "agent5_analysis",
      "type": "LLM",
      "subtype": "GMI",
      "config": {
        "base_url": "https://api.gmi-serving.com/v1",
        "model": "meta-llama/Llama-3.3-70B-Instruct",
        "script": "agents/agent5_analysis.py",
        "function": "run"
      },
      "inputs": ["transcript_payload"],
      "outputs": ["analysis_payload"]
    },
    {
      "id": "output_assembler",
      "type": "Tool",
      "subtype": "Python",
      "config": {
        "script": "agents/output_assembler.py",
        "function": "run"
      },
      "inputs": [
        "audio_payload",
        "transcript_payload",
        "subtitle_payload",
        "stat_events_payload",
        "analysis_payload"
      ],
      "outputs": ["final_output"]
    },
    {
      "id": "sink",
      "type": "Infrastructure",
      "subtype": "Output",
      "config": {
        "format": "json"
      },
      "inputs": ["final_output"]
    }
  ],
  "lanes": [
    { "from": "source.raw_input", "to": "agent1_ingest.raw_input" },
    {
      "from": "agent1_ingest.audio_payload",
      "to": "agent2_transcribe.audio_payload"
    },
    {
      "from": "agent2_transcribe.transcript_payload",
      "to": "agent3_translate.transcript_payload"
    },
    {
      "from": "agent2_transcribe.transcript_payload",
      "to": "agent4_stats.transcript_payload"
    },
    {
      "from": "agent2_transcribe.transcript_payload",
      "to": "agent5_analysis.transcript_payload"
    },
    {
      "from": "agent3_translate.subtitle_payload",
      "to": "output_assembler.subtitle_payload"
    },
    {
      "from": "agent4_stats.stat_events_payload",
      "to": "output_assembler.stat_events_payload"
    },
    {
      "from": "agent5_analysis.analysis_payload",
      "to": "output_assembler.analysis_payload"
    },
    {
      "from": "agent1_ingest.audio_payload",
      "to": "output_assembler.audio_payload"
    },
    {
      "from": "agent2_transcribe.transcript_payload",
      "to": "output_assembler.transcript_payload"
    },
    { "from": "output_assembler.final_output", "to": "sink.final_output" }
  ]
}
```

> **Parallelism note:** Agents 3, 4, and 5 all consume `transcript_payload` — RocketRide's
> multithreaded C++ runtime will fan them out in parallel automatically once Agent 2 completes.

### Output Assembler

```python
# agents/output_assembler.py
import time

def run(
    audio_payload: dict,
    transcript_payload: dict,
    subtitle_payload: dict,
    stat_events_payload: dict,
    analysis_payload: dict
) -> dict:
    return {
        "job_id": transcript_payload["job_id"],
        "source_title": audio_payload.get("source_title"),
        "source_url": audio_payload.get("source_url"),
        "duration_seconds": audio_payload.get("duration_seconds"),
        "transcript": transcript_payload,
        "subtitles": subtitle_payload.get("subtitles", {}),
        "stat_events": stat_events_payload.get("stat_events", []),
        "analysis": analysis_payload,
        "processed_at": time.time()
    }
```

---

## 10. GMI Cloud Inference Integration

### OpenAI-Compatible Client Setup

```python
# utils/gmi_client.py
import openai
import os

def get_gmi_client() -> openai.OpenAI:
    """Returns a configured OpenAI client pointing to GMI Cloud."""
    return openai.OpenAI(
        base_url="https://api.gmi-serving.com/v1",
        api_key=os.environ["GMI_API_KEY"]
    )

def list_available_models() -> list:
    """List all models currently available on GMI Cloud."""
    client = get_gmi_client()
    return [m.id for m in client.models.list().data]
```

### Recommended Model IDs on GMI Cloud

Run `list_available_models()` at startup to confirm these are active (model availability
can change). Fallback pairs listed:

| Agent             | Primary                             | Fallback                             |
| ----------------- | ----------------------------------- | ------------------------------------ |
| Translation       | `meta-llama/Llama-3.3-70B-Instruct` | `mistralai/Mistral-7B-Instruct-v0.3` |
| Stat extraction   | Gemini (Google AI Studio)           | `deepseek-ai/DeepSeek-R1` on GMI     |
| Summary/Sentiment | `meta-llama/Llama-3.3-70B-Instruct` | `google/gemma-3-27b-it`              |

### Usage Tracking

GMI Cloud returns token usage in every response. Log it for the judges:

```python
# After any GMI call:
usage = response.usage
print(f"[GMI] {model} — prompt: {usage.prompt_tokens}, "
      f"completion: {usage.completion_tokens}, total: {usage.total_tokens}")
```

---

## 11. Player Stats Database

**File:** `data/players.json`

Curated World Cup 2026 squad data. Build this once before the hackathon using publicly
available FIFA/Transfermarkt data or generate a realistic mock.

### Schema

```json
[
  {
    "name": "Kylian Mbappé",
    "aliases": ["Mbappe", "Mbappé", "Kylian"],
    "nation": "France",
    "club": "Real Madrid",
    "position": "FW",
    "age": 27,
    "caps": 87,
    "goals_international": 49,
    "tournament_goals": 3,
    "tournament_assists": 1,
    "tournament_appearances": 4,
    "tournament_minutes": 356,
    "tournament_yellow_cards": 1,
    "tournament_red_cards": 0,
    "club_season_goals": 28,
    "club_season_assists": 9,
    "market_value_m": 180
  },
  {
    "name": "Erling Haaland",
    "aliases": ["Haaland", "Erling"],
    "nation": "Norway",
    "club": "Manchester City",
    "position": "ST",
    "age": 25,
    "caps": 42,
    "goals_international": 31,
    "tournament_goals": 4,
    "tournament_assists": 0,
    "tournament_appearances": 4,
    "tournament_minutes": 360,
    "tournament_yellow_cards": 0,
    "tournament_red_cards": 0,
    "club_season_goals": 32,
    "club_season_assists": 5,
    "market_value_m": 200
  }
]
```

Include ~40 players covering top nations (France, Brazil, England, Argentina, Spain,
Germany, Portugal, Norway). The fuzzy matcher in Agent 4 handles nickname variants.

### Build Script

```python
# scripts/build_players_db.py
"""
Run once to build the player database.
Extend with real data from: https://www.transfermarkt.com/weltmeisterschaft-2026
or mock the tournament stats for hackathon purposes.
"""
import json

# Seed with key players — extend this list
PLAYERS = [
    # ... entries as above ...
]

with open("data/players.json", "w") as f:
    json.dump(PLAYERS, f, indent=2, ensure_ascii=False)

print(f"Wrote {len(PLAYERS)} players to data/players.json")
```

---

## 12. FastAPI Wrapper (Frontend Bridge)

This is not the frontend — it's the API layer that lets any frontend (or demo curl command)
talk to the RocketRide pipeline via HTTP.

**File:** `api/main.py`

```python
# api/main.py
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uuid
import asyncio
import httpx
import json

app = FastAPI(title="World Cup AI Broadcast API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten for production
    allow_methods=["*"],
    allow_headers=["*"]
)

# In-memory job store (fine for hackathon)
JOB_STORE: dict[str, dict] = {}

ROCKETRIDE_URL = "http://localhost:5565/process"

class ProcessRequest(BaseModel):
    source_type: str           # "youtube_url" | "file_path"
    source_value: str
    target_languages: list[str] = ["es", "pt", "fr", "ar", "ja"]

class JobStatus(BaseModel):
    job_id: str
    status: str                # queued | processing | complete | error
    result: Optional[dict] = None
    error: Optional[str] = None

@app.post("/process", response_model=JobStatus)
async def submit_job(req: ProcessRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    JOB_STORE[job_id] = {"status": "queued", "result": None, "error": None}
    background_tasks.add_task(run_pipeline, job_id, req)
    return JobStatus(job_id=job_id, status="queued")

async def run_pipeline(job_id: str, req: ProcessRequest):
    JOB_STORE[job_id]["status"] = "processing"
    payload = {
        "job_id": job_id,
        "source_type": req.source_type,
        "source_value": req.source_value,
        "target_languages": req.target_languages
    }
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(ROCKETRIDE_URL, json=payload)
            response.raise_for_status()
            result = response.json()
            JOB_STORE[job_id]["status"] = "complete"
            JOB_STORE[job_id]["result"] = result
    except Exception as e:
        JOB_STORE[job_id]["status"] = "error"
        JOB_STORE[job_id]["error"] = str(e)

@app.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job(job_id: str):
    if job_id not in JOB_STORE:
        raise HTTPException(status_code=404, detail="Job not found")
    job = JOB_STORE[job_id]
    return JobStatus(job_id=job_id, **job)

@app.get("/health")
async def health():
    return {"status": "ok"}
```

### Running the API

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Example curl (for demo)

```bash
curl -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "youtube_url",
    "source_value": "https://www.youtube.com/watch?v=REAL_WORLDCUP_INTERVIEW",
    "target_languages": ["es", "pt", "fr"]
  }'
# Returns: {"job_id": "...", "status": "queued"}

# Poll for result:
curl http://localhost:8000/jobs/<job_id>
```

---

## 13. Project File Structure

```
worldcup-ai-broadcast/
├── README.md
├── .env                          # API keys — never commit
├── .env.example                  # Template for teammates
├── requirements.txt
├── docker-compose.yml
│
├── pipeline/
│   └── worldcup_broadcast.pipe   # RocketRide pipeline definition
│
├── agents/
│   ├── agent1_ingest.py
│   ├── agent2_transcribe.py
│   ├── agent3_translate.py
│   ├── agent4_stats.py
│   ├── agent5_analysis.py
│   └── output_assembler.py
│
├── api/
│   └── main.py                   # FastAPI wrapper
│
├── utils/
│   ├── gmi_client.py             # GMI Cloud OpenAI-compat client
│   └── schemas.py                # Pydantic models / TypedDicts
│
├── data/
│   └── players.json              # World Cup player stats DB
│
├── scripts/
│   ├── build_players_db.py       # Generate/seed players.json
│   └── test_pipeline.py          # End-to-end integration test
│
└── tests/
    ├── test_agent1.py
    ├── test_agent2.py
    ├── test_agent3.py
    ├── test_agent4.py
    └── test_agent5.py
```

---

## 14. Environment Variables

**File:** `.env` (never commit — add to `.gitignore`)

```bash
# Google AI Studio
GOOGLE_API_KEY=AIza...

# GMI Cloud
GMI_API_KEY=gmi_...

# Optional: override GMI base URL if they provide a different endpoint at event
GMI_BASE_URL=https://api.gmi-serving.com/v1

# Pipeline config
JOBS_DIR=/tmp/jobs
PLAYERS_DB_PATH=data/players.json
LOG_LEVEL=INFO
```

**File:** `.env.example`

```bash
GOOGLE_API_KEY=your_google_api_key_here
GMI_API_KEY=your_gmi_api_key_here
GMI_BASE_URL=https://api.gmi-serving.com/v1
JOBS_DIR=/tmp/jobs
PLAYERS_DB_PATH=data/players.json
LOG_LEVEL=INFO
```

---

## 15. Build Order & Time Estimates

Follow this order strictly — each agent unlocks the next test.

| #         | Task                                                                         | Time       | Owner    |
| --------- | ---------------------------------------------------------------------------- | ---------- | -------- |
| 1         | Clone RocketRide repo, install AIDE VS Code extension, confirm engine starts | 20 min     | All      |
| 2         | Get GMI Cloud API key, run `list_available_models()`, confirm connectivity   | 10 min     | 1 person |
| 3         | Get Google AI Studio API key, test a simple Gemini call                      | 10 min     | 1 person |
| 4         | Build `data/players.json` with 20–40 players                                 | 20 min     | 1 person |
| 5         | Build + test Agent 1 (ingest) with a local audio file                        | 30 min     | Dev A    |
| 6         | Build + test Agent 2 (transcription) against Agent 1 output                  | 45 min     | Dev A    |
| 7         | Build + test Agent 3 (translation) against hardcoded transcript              | 30 min     | Dev B    |
| 8         | Build + test Agent 4 (stat extraction) against hardcoded transcript          | 45 min     | Dev B    |
| 9         | Build + test Agent 5 (summary/sentiment) against hardcoded transcript        | 25 min     | Dev A    |
| 10        | Wire `.pipe` file in RocketRide AIDE, connect all nodes                      | 30 min     | All      |
| 11        | Full end-to-end test with a real YouTube interview                           | 20 min     | All      |
| 12        | FastAPI wrapper + test curl commands                                         | 25 min     | Dev B    |
| 13        | Polish error handling, logging, graceful degradation                         | 20 min     | All      |
| 14        | GitHub repo setup, README, demo script rehearsal                             | 20 min     | All      |
| **Total** |                                                                              | **~6 hrs** |          |

---

## 16. Testing Strategy

### Unit Tests (per agent, with mocked inputs)

```python
# tests/test_agent4.py
import pytest
import json
from agents.agent4_stats import run, fuzzy_lookup_player

def test_fuzzy_lookup_mbappe():
    player = fuzzy_lookup_player("Mbappe")
    assert player is not None
    assert "Mbappé" in player["name"]

def test_fuzzy_lookup_typo():
    player = fuzzy_lookup_player("Mabppe")  # typo
    assert player is not None  # should still match

def test_run_with_sample_transcript():
    sample = {
        "job_id": "test-001",
        "segments": [
            {"id": 0, "start": 0.0, "end": 4.0, "speaker": "REPORTER",
             "text": "Mbappe, you scored 3 goals tonight."},
            {"id": 1, "start": 4.2, "end": 8.0, "speaker": "PLAYER",
             "text": "Yes, I'm happy with my hat-trick and 2 assists this tournament."}
        ],
        "full_text": "..."
    }
    result = run(sample)
    assert "stat_events" in result
    assert len(result["stat_events"]) > 0
```

### Integration Test

```python
# scripts/test_pipeline.py
"""
Full pipeline smoke test using a short audio clip.
Run this before the demo.
"""
import json
from agents import (
    agent1_ingest, agent2_transcribe, agent3_translate,
    agent4_stats, agent5_analysis, output_assembler
)

TEST_AUDIO = "tests/fixtures/sample_interview_30s.wav"

def test_full_pipeline():
    # Agent 1
    audio = agent1_ingest.run({
        "source_type": "file_path",
        "source_value": TEST_AUDIO,
        "target_languages": ["es"],
        "job_id": "smoke-test-001"
    })
    print(f"✓ Agent 1: {audio['duration_seconds']:.1f}s audio")

    # Agent 2
    transcript = agent2_transcribe.run(audio)
    assert len(transcript["segments"]) > 0
    print(f"✓ Agent 2: {transcript['word_count']} words, "
          f"{len(transcript['segments'])} segments")

    # Agents 3, 4, 5 (can run in parallel in prod, sequential here for debugging)
    subtitles = agent3_translate.run({**transcript, "target_languages": ["es"]})
    print(f"✓ Agent 3: {list(subtitles['subtitles'].keys())} languages")

    stats = agent4_stats.run(transcript)
    print(f"✓ Agent 4: {len(stats['stat_events'])} stat events")

    analysis = agent5_analysis.run(transcript)
    print(f"✓ Agent 5: sentiment={analysis['overall_sentiment']}, "
          f"bullets={len(analysis['summary_bullets'])}")

    # Final assembly
    final = output_assembler.run(audio, transcript, subtitles, stats, analysis)
    print(f"\n✅ Pipeline complete!")
    print(json.dumps(final, indent=2, ensure_ascii=False)[:1000] + "...")

if __name__ == "__main__":
    test_full_pipeline()
```

---

## 17. Demo Payload (Sample Inputs & Expected Outputs)

### Input

```json
{
  "source_type": "youtube_url",
  "source_value": "https://www.youtube.com/watch?v=<real_wc_interview>",
  "target_languages": ["es", "pt", "fr"],
  "job_id": "demo-live-001"
}
```

### Expected Output (truncated)

```json
{
  "job_id": "demo-live-001",
  "source_title": "Mbappé Post-Match Press Conference | France vs Brazil",
  "duration_seconds": 312.4,
  "transcript": {
    "detected_language": "fr",
    "word_count": 634,
    "segments": [
      {
        "id": 0,
        "start": 0.0,
        "end": 5.1,
        "speaker": "REPORTER",
        "text": "Kylian, ce soir tu as marqué deux buts...",
        "confidence": 0.96
      },
      {
        "id": 1,
        "start": 5.4,
        "end": 11.2,
        "speaker": "PLAYER",
        "text": "Oui, je suis vraiment content...",
        "confidence": 0.94
      }
    ]
  },
  "subtitles": {
    "en": [
      {
        "id": 0,
        "start": 0.0,
        "end": 5.1,
        "text": "Kylian, tonight you scored two goals..."
      }
    ],
    "es": [
      {
        "id": 0,
        "start": 0.0,
        "end": 5.1,
        "text": "Kylian, esta noche marcaste dos goles..."
      }
    ],
    "pt": [
      {
        "id": 0,
        "start": 0.0,
        "end": 5.1,
        "text": "Kylian, esta noite você marcou dois gols..."
      }
    ]
  },
  "stat_events": [
    {
      "segment_id": 1,
      "timestamp_start": 5.4,
      "timestamp_end": 11.2,
      "player_name": "Mbappé",
      "stat_category": "goals",
      "mentioned_value": "2",
      "highlight_text": "tu as marqué deux buts",
      "player_card": {
        "name": "Kylian Mbappé",
        "club": "Real Madrid",
        "nation": "France",
        "tournament_goals": 5,
        "tournament_assists": 2
      }
    }
  ],
  "analysis": {
    "summary_bullets": [
      "Scored two goals, credits tactical setup from manager",
      "Dismissed injury concerns, expects to be fit for quarterfinal",
      "Praised Brazilian team despite France winning"
    ],
    "overall_sentiment": "confident",
    "speaker_sentiment": { "PLAYER": "confident", "REPORTER": "neutral" }
  }
}
```

---

## 18. Phase 2 Roadmap (Post-Hackathon)

Show this slide during your demo — it tells the story of where the product goes.

| Phase | Feature                                                                     | Tech                             |
| ----- | --------------------------------------------------------------------------- | -------------------------------- |
| 2A    | Audio dubbing — translate + synthesize in target language                   | GMI Cloud TTS (Kokoro / XTTS-v2) |
| 2B    | Real-time streaming — process live press conference audio                   | WebSockets + Gemini Live API     |
| 2C    | Clip extraction — auto-cut highlight moments to short clips                 | ffmpeg + stat_event timestamps   |
| 2D    | Broadcast overlay renderer — burn subtitles + stat cards into video         | OpenCV + PIL                     |
| 2E    | Historical stat queries — "How many goals has Mbappe scored in World Cups?" | RAG over stats DB with Pinecone  |
| 2F    | Multi-feed support — parallel processing of 4+ press conferences            | RocketRide horizontal scaling    |

---

_Built for the GDG Newport Beach × RocketRide × GMI Cloud Hackathon — May 2026_  
_Pipeline: RocketRide AIDE | Transcription: Google Gemini 2.0 Flash | Inference: GMI Cloud H100/H200_
