from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

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


def _extract_local(transcript: TranscriptPayload) -> list[StatEvent]:
    players = load_players()
    events: list[StatEvent] = []
    seen: set[tuple[int, str, str]] = set()

    for segment in transcript.segments:
        lowered = segment.text.lower()
        categories = [
            category
            for category, terms in STAT_CATEGORIES.items()
            if any(term in lowered for term in terms)
        ] or ["general"]

        for player in players:
            names = [player["name"], *player.get("aliases", [])]
            if not any(re.search(rf"\b{re.escape(name.lower())}\b", lowered) for name in names):
                continue
            for category in categories:
                key = (segment.id, player["name"], category)
                if key in seen:
                    continue
                seen.add(key)
                events.append(
                    StatEvent(
                        segment_id=segment.id,
                        timestamp_start=segment.start,
                        timestamp_end=segment.end,
                        player_name=player["name"],
                        stat_category=category,
                        mentioned_value=_mentioned_value(segment.text),
                        highlight_text=segment.text,
                        player_card=player,
                    )
                )
    return events


def run(transcript_payload: dict) -> dict:
    transcript = TranscriptPayload.model_validate(transcript_payload)
    events = _extract_local(transcript)
    return {"job_id": transcript.job_id, "stat_events": [event.model_dump() for event in events]}

