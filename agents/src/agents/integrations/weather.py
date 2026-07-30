"""Weather data via wttr.in."""

from __future__ import annotations

import json
from urllib.parse import quote
from urllib.request import urlopen


def fetch_weather(city: str) -> dict:
    """Return structured weather for a city."""
    city = city.strip()
    if not city:
        raise ValueError("City is required")

    url = f"https://wttr.in/{quote(city)}?format=j1"
    with urlopen(url, timeout=10) as response:
        data = json.load(response)

    current = data["current_condition"][0]
    description = current["weatherDesc"][0]["value"]
    return {
        "city": city,
        "temp_c": current["temp_C"],
        "temp_f": current["temp_F"],
        "description": description,
        "feels_like_c": current.get("FeelsLikeC", current["temp_C"]),
        "humidity": current.get("humidity", ""),
    }


def format_weather(data: dict) -> str:
    return (
        f"{data['city']}: {data['temp_c']}°C ({data['temp_f']}°F), "
        f"{data['description']}"
    )
