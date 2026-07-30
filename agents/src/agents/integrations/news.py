"""News headline fetchers — NewsAPI (primary) or Google News RSS (fallback)."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

_USER_AGENT = "DailyAgentHub/0.1 (marti-io)"


def fetch_news_articles(
    topic: str,
    *,
    api_key: str | None = None,
    max_articles: int = 5,
) -> tuple[list[dict], str]:
    """Return recent news articles and the provider name."""
    topic = topic.strip()
    if not topic:
        raise ValueError("Please provide a topic to search for news.")

    errors: list[str] = []
    if api_key:
        try:
            return _newsapi_articles(topic, api_key=api_key, max_articles=max_articles), "NewsAPI"
        except (
            HTTPError,
            URLError,
            json.JSONDecodeError,
            KeyError,
            IndexError,
        ) as exc:
            errors.append(f"NewsAPI: {exc}")

    try:
        return _google_rss_articles(topic, max_articles=max_articles), "Google News"
    except (HTTPError, URLError, ET.ParseError) as exc:
        errors.append(f"Google News RSS: {exc}")

    detail = "; ".join(errors) if errors else "no providers configured"
    raise RuntimeError(
        f"Could not fetch news for '{topic}' ({detail}). "
        "Set NEWS_API_KEY for NewsAPI.org, or check your network."
    )


def fetch_news_headlines(
    topic: str,
    *,
    api_key: str | None = None,
    max_articles: int = 5,
) -> str:
    """Return formatted recent headlines for a topic."""
    try:
        articles, source = fetch_news_articles(
            topic, api_key=api_key, max_articles=max_articles
        )
    except (RuntimeError, ValueError) as exc:
        return str(exc)

    if not articles:
        return f"No recent headlines found for '{topic}'."

    lines = [f"Recent headlines about {topic} (via {source}):"]
    for article in articles:
        title = article["title"]
        source_name = article.get("source") or ""
        published = article.get("published") or ""
        suffix_parts = [part for part in (source_name, published) if part]
        suffix = f" ({', '.join(suffix_parts)})" if suffix_parts else ""
        lines.append(f"- {title}{suffix}")
    return "\n".join(lines)


def _request(url: str, *, timeout: int = 10) -> bytes:
    req = Request(url, headers={"User-Agent": _USER_AGENT})
    with urlopen(req, timeout=timeout) as response:
        return response.read()


def _newsapi_articles(topic: str, *, api_key: str, max_articles: int) -> list[dict]:
    query = quote(topic)
    url = (
        "https://newsapi.org/v2/everything"
        f"?q={query}&pageSize={max_articles}&sortBy=publishedAt"
        f"&language=en&apiKey={quote(api_key)}"
    )
    data = json.loads(_request(url))
    if data.get("status") != "ok":
        raise ValueError(data.get("message", "NewsAPI returned an error"))

    articles: list[dict] = []
    for article in data.get("articles") or []:
        title = (article.get("title") or "").strip()
        if not title or title == "[Removed]":
            continue
        articles.append(
            {
                "title": title,
                "source": (article.get("source") or {}).get("name") or "Unknown",
                "published": (article.get("publishedAt") or "")[:10],
                "url": (article.get("url") or "").strip(),
            }
        )
    return articles[:max_articles]


def _google_rss_articles(topic: str, *, max_articles: int) -> list[dict]:
    query = quote(topic)
    url = (
        "https://news.google.com/rss/search"
        f"?q={query}&hl=en-US&gl=US&ceid=US:en"
    )
    root = ET.fromstring(_request(url))
    items = root.findall(".//item")
    if not items:
        return []

    articles: list[dict] = []
    for item in items[:max_articles]:
        title_el = item.find("title")
        pub_el = item.find("pubDate")
        link_el = item.find("link")
        if title_el is None or not (title_el.text or "").strip():
            continue
        title = title_el.text.strip()
        source = _source_from_google_title(title)
        articles.append(
            {
                "title": _headline_from_google_title(title),
                "source": source,
                "published": (pub_el.text or "").strip() if pub_el is not None else "",
                "url": (link_el.text or "").strip() if link_el is not None else "",
            }
        )
    return articles


def _headline_from_google_title(title: str) -> str:
    if " - " not in title:
        return title
    return title.rsplit(" - ", 1)[0].strip()


def _source_from_google_title(title: str) -> str:
    if " - " not in title:
        return ""
    tail = title.rsplit(" - ", 1)[1].strip()
    if tail.startswith("("):
        return ""
    return tail.split(" (", 1)[0].strip()
