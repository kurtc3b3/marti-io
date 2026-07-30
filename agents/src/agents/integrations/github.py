"""GitHub trending repositories — scraped trending APIs with search fallback."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

_USER_AGENT = "DailyAgentHub/0.1 (marti-io)"


def fetch_github_trending_repos(
    language: str = "",
    *,
    since: str = "daily",
    max_repos: int = 5,
) -> tuple[list[dict], str]:
    """Return trending repositories and the provider name."""
    language = language.strip().lower()
    since = since.strip().lower() or "daily"
    if since not in {"daily", "weekly", "monthly"}:
        since = "daily"

    errors: list[str] = []
    try:
        repos = _from_lessx(language=language, since=since)
        return repos[:max_repos], "GitHub Trending"
    except (
        HTTPError,
        URLError,
        json.JSONDecodeError,
        KeyError,
        IndexError,
        TypeError,
        ValueError,
    ) as exc:
        errors.append(f"GitHub trending API: {exc}")

    try:
        repos = _from_doforce(language=language, since=since)
        return repos[:max_repos], "GitHub Trending"
    except (
        HTTPError,
        URLError,
        json.JSONDecodeError,
        KeyError,
        IndexError,
        TypeError,
        ValueError,
    ) as exc:
        errors.append(f"GitHub trending fallback: {exc}")

    try:
        repos = _from_github_search(language=language)
        return repos[:max_repos], "GitHub Search"
    except (
        HTTPError,
        URLError,
        json.JSONDecodeError,
        KeyError,
        IndexError,
    ) as exc:
        errors.append(f"GitHub Search API: {exc}")

    detail = "; ".join(errors) if errors else "no providers available"
    raise RuntimeError(f"Could not fetch GitHub trending repositories ({detail}).")


def fetch_github_trending(
    language: str = "",
    *,
    since: str = "daily",
    max_repos: int = 5,
) -> str:
    """Return formatted trending GitHub repositories."""
    language = language.strip().lower()
    since = since.strip().lower() or "daily"
    if since not in {"daily", "weekly", "monthly"}:
        since = "daily"

    try:
        repos, source = fetch_github_trending_repos(
            language, since=since, max_repos=max_repos
        )
    except RuntimeError as exc:
        return str(exc)

    return _format_repos(
        repos,
        since=since,
        language=language,
        source=source,
        max_repos=max_repos,
    )


def _request(url: str, *, timeout: int = 15) -> bytes:
    req = Request(url, headers={"User-Agent": _USER_AGENT, "Accept": "application/json"})
    with urlopen(req, timeout=timeout) as response:
        return response.read()


def _from_lessx(*, language: str, since: str) -> list[dict]:
    params: dict[str, str] = {"since": since}
    if language:
        params["language"] = language
    url = f"https://githubtrending.lessx.xyz/trending?{urlencode(params)}"
    data = json.loads(_request(url))
    if not isinstance(data, list) or not data:
        raise ValueError("GitHub trending API returned no repositories")
    return [_normalize_lessx(item) for item in data[:10]]


def _from_doforce(*, language: str, since: str) -> list[dict]:
    params: dict[str, str] = {"since": since}
    if language:
        params["lang"] = language
    url = f"https://trend.doforce.dpdns.org/repo?{urlencode(params)}"
    data = json.loads(_request(url))
    if not isinstance(data, list) or not data:
        raise ValueError("GitHub trending fallback returned no repositories")
    return [_normalize_doforce(item) for item in data[:10]]


def _from_github_search(*, language: str) -> list[dict]:
    created_after = (datetime.now(UTC) - timedelta(days=7)).date().isoformat()
    query_parts = [f"created:>{created_after}", "stars:>50"]
    if language:
        query_parts.append(f"language:{language}")
    params = urlencode(
        {
            "q": " ".join(query_parts),
            "sort": "stars",
            "order": "desc",
            "per_page": "10",
        }
    )
    url = f"https://api.github.com/search/repositories?{params}"
    data = json.loads(_request(url))
    items = data.get("items") or []
    if not items:
        raise ValueError("GitHub Search returned no repositories")
    return [_normalize_search(item) for item in items]


def _normalize_lessx(item: dict) -> dict:
    name = (item.get("name") or "").strip()
    if not name:
        raise ValueError("Repository missing name")
    stars = _parse_int(item.get("stars"))
    forks = _parse_int(item.get("forks"))
    return {
        "name": name,
        "url": (item.get("repository") or f"https://github.com/{name}").strip(),
        "language": (item.get("language") or "").strip(),
        "stars": stars,
        "forks": forks,
        "change": (item.get("increased") or "").strip(),
        "description": _truncate((item.get("description") or "").strip()),
    }


def _normalize_doforce(item: dict) -> dict:
    repo = (item.get("repo") or "").strip().lstrip("/")
    if not repo:
        raise ValueError("Repository missing name")
    change = item.get("change")
    change_text = f"{change} stars today" if isinstance(change, int) else ""
    return {
        "name": repo,
        "url": f"https://github.com/{repo}",
        "language": (item.get("lang") or "").strip(),
        "stars": _parse_int(item.get("stars")),
        "forks": _parse_int(item.get("forks")),
        "change": change_text,
        "description": _truncate((item.get("desc") or "").strip()),
    }


def _normalize_search(item: dict) -> dict:
    full_name = (item.get("full_name") or "").strip()
    if not full_name:
        raise ValueError("Repository missing name")
    return {
        "name": full_name,
        "url": (item.get("html_url") or f"https://github.com/{full_name}").strip(),
        "language": (item.get("language") or "").strip(),
        "stars": _parse_int(item.get("stargazers_count")),
        "forks": _parse_int(item.get("forks_count")),
        "change": "",
        "description": _truncate((item.get("description") or "").strip()),
    }


def _format_repos(
    repos: list[dict],
    *,
    since: str,
    language: str,
    source: str,
    max_repos: int = 5,
) -> str:
    scope = language or "all languages"
    lines = [f"Trending GitHub repositories ({since}, {scope}, via {source}):"]
    for repo in repos[:max_repos]:
        lang = f" [{repo['language']}]" if repo.get("language") else ""
        stats = []
        if repo.get("change"):
            stats.append(repo["change"])
        if repo.get("stars"):
            stats.append(f"{repo['stars']:,} stars")
        if repo.get("forks"):
            stats.append(f"{repo['forks']:,} forks")
        stats_text = " · ".join(stats)
        desc = f" — {repo['description']}" if repo.get("description") else ""
        suffix = f" ({stats_text})" if stats_text else ""
        lines.append(f"- {repo['name']}{lang}{suffix}{desc}")
    return "\n".join(lines)


def _parse_int(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        digits = "".join(ch for ch in value if ch.isdigit())
        return int(digits) if digits else 0
    return 0


def _truncate(text: str, limit: int = 120) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."
