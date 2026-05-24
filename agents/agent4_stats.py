from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from utils.api_sports_client import enrich_player_card, is_live_lookup_enabled, redact_api_sports_secret
from utils.json_helpers import parse_json_object
from utils.schemas import StatEvent, TranscriptPayload


STAT_CATEGORIES = {
    "goals": ["goal", "goals", "scored", "hat-trick", "hat trick"],
    "assists": ["assist", "assists"],
    "saves": ["save", "saves"],
    "tackles": ["tackle", "tackles"],
    "yellow_cards": ["yellow card", "booking"],
    "red_cards": ["red card", "sent off"],
    "minutes_played": ["minutes", "played"],
    "shots_on_target": ["shot on target", "shots on target"],
}

NUMBER_WORDS = {
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
    "ten": "10",
}


# ---------------------------------------------------------------------------
# Gemini NER extraction prompt
# ---------------------------------------------------------------------------

GEMINI_NER_PROMPT = """\
You are a sports entity recognition (NER) system for post-game interview transcripts.

Analyze the transcript below and extract EVERY mention of:
1. **Player names** — explicit ("Messi scored") or implicit ("I scored", "that goal", "my assist") where the speaker IS the player
2. **Team names** — explicit team references
3. **Stat types** — goals, assists, saves, tackles, cards, minutes played, shots, appearances, fitness/condition
4. **Implicit references** — "that goal" (= the speaker scored), "my assist", "we won" (= speaker's contribution), "I feel physically well" (= fitness/minutes context)

The speaker in this interview is identified in the metadata. When the speaker says "I" or "my", resolve to their identity.

Return ONLY valid JSON with this shape:
{
  "extractions": [
    {
      "segment_id": 0,
      "player_name": "Lionel Messi",
      "stat_type": "goals",
      "context_phrase": "the exact quote from the transcript",
      "entity_type": "implicit_self_reference",
      "confidence": 0.92
    }
  ]
}

Rules:
- segment_id MUST match the id field from the transcript segments
- player_name should be the full canonical name
- stat_type must be one of: goals, assists, saves, tackles, yellow_cards, red_cards, minutes_played, shots_on_target, general
- entity_type must be one of: explicit_player_mention, implicit_self_reference, implicit_stat_reference, stat_mention, team_mention, fitness_context, match_result_reference, tournament_context, competition_reference
- confidence is 0.0 to 1.0
- Focus on segments with substantive content — skip filler/transition segments
- The interview may be in ANY language (Spanish, Portuguese, etc.) — extract entities from the original text
- For a ~60 segment interview, extract 5-10 high-quality events spread across the timeline
- Do NOT extract from every segment — only those with clear stat/player/competition relevance

TRANSCRIPT METADATA:
Speaker: {speaker_name}
Source: {source_title}
Language: {detected_language}

TRANSCRIPT SEGMENTS:
{segments_json}
"""


def _players_path() -> Path:
    return Path(os.getenv("PLAYERS_DB_PATH", "data/players.json"))


def load_players() -> list[dict[str, Any]]:
    with _players_path().open(encoding="utf-8") as file:
        return json.load(file)


def _choices(players: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    choices: dict[str, dict[str, Any]] = {}
    for player in players:
        choices[player["name"].lower()] = player
        for alias in player.get("aliases", []):
            choices[alias.lower()] = player
    return choices


def _ratio(a: str, b: str) -> int:
    try:
        from rapidfuzz import fuzz

        return int(fuzz.token_sort_ratio(a, b))
    except ImportError:
        from difflib import SequenceMatcher

        return int(SequenceMatcher(None, a, b).ratio() * 100)


def fuzzy_lookup_player(name_mention: str) -> dict | None:
    mention = name_mention.lower().strip()
    choices = _choices(load_players())
    best_name = None
    best_score = 0
    for candidate in choices:
        score = _ratio(mention, candidate)
        if score > best_score:
            best_score = score
            best_name = candidate
    if best_name and best_score >= 70:
        return choices[best_name]
    return None


def _mentioned_value(text: str) -> str:
    digit = re.search(r"\b\d+\b", text)
    if digit:
        return digit.group(0)
    lowered = text.lower()
    for word, value in NUMBER_WORDS.items():
        if re.search(rf"\b{re.escape(word)}\b", lowered):
            return value
    return ""


def _sentences(text: str) -> list[str]:
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
    return parts or [text]


def _categories_for_text(text: str) -> list[str]:
    lowered = text.lower()
    return [
        category
        for category, terms in STAT_CATEGORIES.items()
        if any(term in lowered for term in terms)
    ] or ["general"]


def _mentions_player(text: str, player: dict[str, Any]) -> bool:
    lowered = text.lower()
    names = [player["name"], *player.get("aliases", [])]
    return any(re.search(rf"\b{re.escape(name.lower())}\b", lowered) for name in names)


def _safe_enrich_player_card(player: dict[str, Any]) -> dict[str, Any]:
    try:
        return enrich_player_card(player)
    except Exception as exc:
        return {
            **player,
            "api_sports": {
                "source": "api-sports",
                "sport": "football",
                "status": "error",
                "errors": [
                    {
                        "stage": "unexpected",
                        "message": redact_api_sports_secret(str(exc)),
                    }
                ],
            },
        }


# ---------------------------------------------------------------------------
# Gemini NER extraction path
# ---------------------------------------------------------------------------

def _infer_speaker(transcript: TranscriptPayload) -> str:
    """Try to infer the main speaker from the transcript or source context."""
    # Check if any known player name appears in the source title or full text
    players = load_players()
    full_text = transcript.full_text.lower()
    for player in players:
        names = [player["name"].lower(), *[a.lower() for a in player.get("aliases", [])]]
        for name in names:
            if name in full_text:
                return player["name"]
    return "Unknown Player"


def _build_segment_index(transcript: TranscriptPayload) -> dict[int, Any]:
    """Build a lookup from segment id to segment data."""
    return {seg.id: seg for seg in transcript.segments}


def _extract_with_gemini(transcript: TranscriptPayload) -> list[StatEvent]:
    """Use Gemini to perform NER on the transcript and extract stat events."""
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        print("[agent4_stats] google-genai not installed, falling back to local extraction")
        return _extract_local(transcript)

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("[agent4_stats] GOOGLE_API_KEY not set, falling back to local extraction")
        return _extract_local(transcript)

    speaker_name = _infer_speaker(transcript)
    segments_json = json.dumps(
        [{"id": s.id, "start": s.start, "end": s.end, "speaker": s.speaker, "text": s.text}
         for s in transcript.segments],
        indent=2,
        ensure_ascii=False,
    )

    prompt = GEMINI_NER_PROMPT.format(
        speaker_name=speaker_name,
        source_title=transcript.job_id,
        detected_language=transcript.detected_language,
        segments_json=segments_json,
    )

    model_name = os.getenv("GEMINI_NER_MODEL", "gemini-2.5-flash")
    client = genai.Client(api_key=api_key)

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=[prompt],
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
            ),
        )
        result = parse_json_object(response.text)
    except Exception as exc:
        print(f"[agent4_stats] Gemini NER failed: {exc}, falling back to local extraction")
        return _extract_local(transcript)

    # Convert Gemini extractions into StatEvents
    extractions = result.get("extractions", [])
    seg_index = _build_segment_index(transcript)
    players = load_players()
    choices = _choices(players)
    live_lookup = is_live_lookup_enabled()
    enriched_players: dict[str, dict[str, Any]] = {}
    events: list[StatEvent] = []

    for ext in extractions:
        segment_id = ext.get("segment_id")
        player_name = ext.get("player_name", "")
        stat_type = ext.get("stat_type", "general")
        context_phrase = ext.get("context_phrase", "")
        entity_type = ext.get("entity_type", "explicit_player_mention")
        confidence = ext.get("confidence", 0.5)

        # Skip low-confidence extractions
        if confidence < 0.5:
            continue

        # Resolve segment timestamps
        seg = seg_index.get(segment_id)
        if not seg:
            continue

        # Look up player card from local DB
        player_card = None
        lookup_name = player_name.lower().strip()
        if lookup_name in choices:
            player_card = choices[lookup_name]
        else:
            # Try fuzzy match
            matched = fuzzy_lookup_player(player_name)
            if matched:
                player_card = matched

        if player_card is None:
            # Create a minimal card for unknown players
            player_card = {"name": player_name, "nation": "Unknown", "position": "Unknown"}

        # Optionally enrich with API-SPORTS
        if live_lookup and player_card.get("name"):
            pname = player_card["name"]
            if pname not in enriched_players:
                enriched_players[pname] = _safe_enrich_player_card(player_card)
            player_card = enriched_players[pname]

        events.append(
            StatEvent(
                segment_id=segment_id,
                timestamp_start=seg.start,
                timestamp_end=seg.end,
                player_name=player_card.get("name", player_name),
                stat_category=stat_type,
                mentioned_value=_mentioned_value(context_phrase or seg.text),
                highlight_text=context_phrase or seg.text,
                player_card=player_card,
                gemini_extraction={
                    "entity_type": entity_type,
                    "context": context_phrase,
                    "confidence": confidence,
                },
            )
        )

    return events


# ---------------------------------------------------------------------------
# Local keyword-based extraction (original fallback)
# ---------------------------------------------------------------------------

def _extract_local(transcript: TranscriptPayload) -> list[StatEvent]:
    players = load_players()
    events: list[StatEvent] = []
    seen: set[tuple[int, str, str]] = set()
    live_lookup = is_live_lookup_enabled()
    enriched_players: dict[str, dict[str, Any]] = {}

    for segment in transcript.segments:
        for sentence in _sentences(segment.text):
            categories = _categories_for_text(sentence)
            mentioned_value = _mentioned_value(sentence)

            for player in players:
                if not _mentions_player(sentence, player):
                    continue
                for category in categories:
                    key = (segment.id, player["name"], category)
                    if key in seen:
                        continue
                    seen.add(key)
                    player_card = player
                    if live_lookup:
                        if player["name"] not in enriched_players:
                            enriched_players[player["name"]] = _safe_enrich_player_card(player)
                        player_card = enriched_players[player["name"]]
                    events.append(
                        StatEvent(
                            segment_id=segment.id,
                            timestamp_start=segment.start,
                            timestamp_end=segment.end,
                            player_name=player["name"],
                            stat_category=category,
                            mentioned_value=mentioned_value,
                            highlight_text=sentence,
                            player_card=player_card,
                        )
                    )
    return events


def run_local(transcript_payload: dict) -> dict:
    """Fast keyword-only extraction — no AI calls, safe to run on partial transcripts."""
    transcript = TranscriptPayload.model_validate(transcript_payload)
    events = _extract_local(transcript)
    return {"job_id": transcript.job_id, "stat_events": [event.model_dump() for event in events]}


def run(transcript_payload: dict) -> dict:
    transcript = TranscriptPayload.model_validate(transcript_payload)

    # Use Gemini NER when not in mock mode
    use_gemini = os.getenv("MOCK_AI", "").lower() not in {"1", "true", "yes"}
    if use_gemini:
        events = _extract_with_gemini(transcript)
    else:
        events = _extract_local(transcript)

    return {"job_id": transcript.job_id, "stat_events": [event.model_dump() for event in events]}
