"""Daily dashboard data for the home screen."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Query

from agents.integrations.dictionary import fetch_word_data
from agents.integrations.github import fetch_github_trending_repos
from agents.integrations.news import fetch_news_articles
from agents.integrations.weather import fetch_weather
from agents.settings import get_settings

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _section(status: str = "ok", **payload: object) -> dict:
    return {"status": status, **payload}


@router.get("")
async def daily_dashboard(
    city: str = Query(default="London", min_length=1, max_length=64),
    news_topic: str = Query(default="technology", min_length=1, max_length=64),
) -> dict:
    settings = get_settings()
    now = datetime.now(UTC)

    try:
        weather = _section(**fetch_weather(city))
    except Exception as exc:
        weather = _section(city=city, error=str(exc), status="error")

    try:
        articles, provider = fetch_news_articles(
            news_topic,
            api_key=settings.news_api_key,
        )
        news = _section(
            topic=news_topic,
            provider=provider,
            articles=articles,
        )
    except Exception as exc:
        news = _section(topic=news_topic, articles=[], error=str(exc), status="error")

    try:
        vocabulary = _section(**fetch_word_data())
    except Exception as exc:
        vocabulary = _section(error=str(exc), status="error")

    try:
        repos, provider = fetch_github_trending_repos()
        github = _section(provider=provider, repos=repos)
    except Exception as exc:
        github = _section(repos=[], error=str(exc), status="error")

    return {
        "date": now.strftime("%A, %B %d, %Y"),
        "greeting": _greeting(now.hour),
        "weather": weather,
        "news": news,
        "vocabulary": vocabulary,
        "github": github,
    }


def _greeting(hour: int) -> str:
    if hour < 12:
        return "Good morning"
    if hour < 18:
        return "Good afternoon"
    return "Good evening"
