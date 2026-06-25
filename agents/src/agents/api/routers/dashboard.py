"""Daily dashboard data for the home screen."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Query

from agents.graphs.daily import get_weather, github_trending, search_news, word_of_the_day

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _card(card_id: str, title: str, content: str, *, status: str = "ok") -> dict:
    return {
        "id": card_id,
        "title": title,
        "content": content,
        "status": status,
        "updated_at": datetime.now(UTC).isoformat(),
    }


@router.get("")
async def daily_dashboard(
    city: str = Query(default="London", min_length=1, max_length=64),
    news_topic: str = Query(default="technology", min_length=1, max_length=64),
) -> dict:
    cards: list[dict] = []

    try:
        weather = get_weather.invoke({"city": city})
        cards.append(_card("weather", f"Weather · {city}", weather))
    except Exception as exc:
        cards.append(_card("weather", f"Weather · {city}", str(exc), status="error"))

    try:
        news = search_news.invoke({"topic": news_topic})
        cards.append(_card("news", "News", news))
    except Exception as exc:
        cards.append(_card("news", "News", str(exc), status="error"))

    try:
        word = word_of_the_day.invoke({})
        cards.append(_card("vocabulary", "Word of the day", word))
    except Exception as exc:
        cards.append(_card("vocabulary", "Word of the day", str(exc), status="error"))

    try:
        repos = github_trending.invoke({"language": ""})
        cards.append(_card("github", "GitHub trending", repos))
    except Exception as exc:
        cards.append(_card("github", "GitHub trending", str(exc), status="error"))

    now = datetime.now(UTC)
    return {
        "date": now.strftime("%A, %B %d, %Y"),
        "greeting": _greeting(now.hour),
        "cards": cards,
    }


def _greeting(hour: int) -> str:
    if hour < 12:
        return "Good morning"
    if hour < 18:
        return "Good afternoon"
    return "Good evening"
