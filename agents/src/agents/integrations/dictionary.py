"""Word of the day — Merriam-Webster via freeapi.me with dictionary fallback."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

_USER_AGENT = "DailyAgentHub/0.1 (marti-io)"

_WORD_POOL = (
    "serendipity",
    "ephemeral",
    "quintessential",
    "luminous",
    "resilient",
    "ubiquitous",
    "eloquent",
    "pragmatic",
    "meticulous",
    "ambivalent",
    "paradigm",
    "catalyst",
    "tenacious",
    "benevolent",
    "scrutinize",
    "diligent",
    "altruistic",
    "capricious",
    "perseverance",
)


def fetch_word_data() -> dict:
    """Return structured word-of-the-day data."""
    errors: list[str] = []
    try:
        return _freeapi_word()
    except (
        HTTPError,
        URLError,
        json.JSONDecodeError,
        KeyError,
        IndexError,
        TypeError,
        ValueError,
    ) as exc:
        errors.append(f"Word of the day API: {exc}")

    try:
        word = _daily_word_from_pool()
        return _dictionary_word(word, label="Dictionary fallback")
    except (
        HTTPError,
        URLError,
        json.JSONDecodeError,
        KeyError,
        IndexError,
    ) as exc:
        errors.append(f"Dictionary API: {exc}")

    detail = "; ".join(errors) if errors else "no providers available"
    raise RuntimeError(f"Could not fetch word of the day ({detail}).")


def fetch_word_of_the_day() -> str:
    """Return today's word with definition and example usage."""
    try:
        data = fetch_word_data()
    except RuntimeError as exc:
        return str(exc)
    return _format_word(data)


def _freeapi_word() -> dict:
    data = json.loads(_request("https://wordoftheday.freeapi.me/"))
    word = (data.get("word") or "").strip()
    definition = (data.get("definition") or "").strip()
    if not word or not definition:
        raise ValueError("Word of the day API returned incomplete data")
    return {
        "word": word,
        "part_of_speech": (data.get("partOfSpeech") or "").strip(),
        "pronunciation": (data.get("pronunciation") or "").strip(),
        "definition": definition,
        "example": (data.get("example") or "").strip(),
        "etymology": (data.get("etymology") or "").strip(),
        "source": (data.get("source") or "Merriam-Webster").strip(),
        "date": (data.get("date") or date.today().isoformat()).strip(),
    }


def _dictionary_word(word: str, *, label: str) -> dict:
    url = (
        "https://api.dictionaryapi.dev/api/v2/entries/en/"
        f"{quote(word)}"
    )
    entries = json.loads(_request(url))
    if not entries:
        raise ValueError(f"No dictionary entry for '{word}'")
    return _dictionary_entry_data(entries[0], label=label)


def _dictionary_entry_data(entry: dict, *, label: str) -> dict:
    word = (entry.get("word") or "").strip()
    phonetic = (entry.get("phonetic") or "").strip()
    meanings = entry.get("meanings") or []
    if not word or not meanings:
        raise ValueError("Dictionary entry missing word or meanings")

    meaning = meanings[0]
    pos = (meaning.get("partOfSpeech") or "").strip()
    definitions = meaning.get("definitions") or []
    if not definitions:
        raise ValueError("Dictionary entry missing definitions")

    definition = (definitions[0].get("definition") or "").strip()
    example = (definitions[0].get("example") or "").strip()
    if not definition:
        raise ValueError("Dictionary entry missing definition text")

    return {
        "word": word,
        "part_of_speech": pos,
        "pronunciation": phonetic,
        "definition": definition,
        "example": example,
        "etymology": "",
        "source": label,
        "date": date.today().isoformat(),
    }


def _format_word(data: dict) -> str:
    header = _format_header(
        data["word"],
        data.get("part_of_speech", ""),
        data.get("pronunciation", ""),
    )
    lines = [f"{header}: {data['definition']}."]
    if data.get("example"):
        lines.append(f"Example: {data['example']}")
    if data.get("etymology"):
        lines.append(f"Etymology: {data['etymology']}")
    if data.get("source") and data.get("date"):
        lines.append(f"Source: {data['source']} word of the day ({data['date']})")
    return "\n".join(lines)


def _request(url: str, *, timeout: int = 10) -> bytes:
    req = Request(url, headers={"User-Agent": _USER_AGENT})
    with urlopen(req, timeout=timeout) as response:
        return response.read()

def _format_header(word: str, pos: str, pronunciation: str) -> str:
    title = word.title() if word.islower() else word
    pos_suffix = f" ({pos})" if pos else ""
    pron_suffix = f", {pronunciation}" if pronunciation else ""
    return f"{title}{pos_suffix}{pron_suffix}"


def _daily_word_from_pool() -> str:
    today = date.today().isoformat()
    digest = hashlib.sha256(today.encode()).hexdigest()
    idx = int(digest[:8], 16) % len(_WORD_POOL)
    return _WORD_POOL[idx]
