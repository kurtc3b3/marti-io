"""Agent registry routes."""

from fastapi import APIRouter

from agents.graphs.daily import TOOLS

router = APIRouter(prefix="/agents", tags=["agents"])

AGENT_CATALOG = [
    {
        "id": "simple",
        "pattern": "react",
        "description": "Single ReAct agent with shared tools",
    },
    {
        "id": "map_reduce",
        "pattern": "map_reduce",
        "description": "Parallel domain workers with synthesize step",
    },
    {
        "id": "swarm",
        "pattern": "swarm",
        "description": "Multi-agent handoffs (see agent-toolkit examples/swarm.py)",
        "status": "planned",
    },
]

PLATFORM_INTEGRATIONS = [
    {"id": "weather", "status": "tool", "notes": "wttr.in via get_weather"},
    {"id": "news", "status": "tool", "notes": "NewsAPI.org or Google News RSS via search_news"},
    {
        "id": "dictionary",
        "status": "tool",
        "notes": "Merriam-Webster WOTD via wordoftheday.freeapi.me",
    },
    {"id": "markets", "status": "planned", "notes": "Market data feed"},
    {
        "id": "github",
        "status": "tool",
        "notes": "GitHub trending via githubtrending.lessx.xyz",
    },
    {"id": "rag", "status": "planned", "notes": "Local document retrieval"},
    {"id": "sqlite", "status": "planned", "notes": "Read-only DB queries"},
    {"id": "email", "status": "planned", "notes": "Triage classifier"},
    {"id": "mastodon", "status": "planned"},
    {"id": "x", "status": "planned"},
    {"id": "discord", "status": "planned"},
    {"id": "slack", "status": "planned"},
    {"id": "mcp", "status": "planned", "notes": "External MCP tool servers"},
    {"id": "a2a", "status": "planned", "notes": "Agent-to-agent protocol"},
]


@router.get("")
async def list_agents() -> dict:
    return {
        "graphs": AGENT_CATALOG,
        "tools": [{"name": t.name, "description": t.description} for t in TOOLS],
        "platforms": PLATFORM_INTEGRATIONS,
    }
