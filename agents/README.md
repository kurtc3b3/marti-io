# Daily Agent Hub

Multi-agent personal assistant API built with **FastAPI**, **LangGraph**, **PostgreSQL** (thread memory), **Redis** (WebSocket pub/sub), and a **TypeScript** web UI.

Integrations: **news** (NewsAPI / Google News RSS), **weather** (wttr.in), **vocabulary** (Merriam-Webster word of the day), **GitHub trending**, and more planned — markets, RAG, SQLite, email triage, Mastodon, X, Discord, Slack, MCP tools, and A2A agent communication.

## Quick start (Docker)

```bash
cd agents
cp .env.template .env   # set OPENAI_API_KEY (optional: NEWS_API_KEY)
docker compose up --build
```

- Web UI: http://localhost:8000/
- API health: http://localhost:8000/api/health/ready
- Swagger (dev only): http://localhost:8000/docs

## Quick start (local)

Start Postgres and Redis (or use Docker for infra only):

```bash
docker compose up postgres redis -d
```

```bash
cd agents
cp .env.template .env   # add OPENAI_API_KEY
uv sync
cd web && npm install && npm run build && cd ..
uv run daily-api
```

## API routes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Liveness |
| GET | `/api/health/ready` | Postgres + Redis readiness |
| GET | `/api/info` | App metadata |
| GET | `/api/agents` | Graph patterns, tools, platform roadmap |
| WS | `/api/chat/ws?thread_id=…` | Streaming chat (primary) |
| POST | `/api/chat` | REST chat (legacy, rate limited) |
| GET | `/api/chat/threads/{id}` | Thread message history |

### WebSocket protocol

Client sends:

```json
{"type": "chat", "message": "What's the weather in Paris?", "graph": "simple"}
```

Server streams via Redis pub/sub:

```json
{"type": "token", "content": "..."}
{"type": "tool_start", "name": "get_weather"}
{"type": "done", "thread_id": "...", "response": "..."}
```

## Memory & transport

- **PostgreSQL** — LangGraph `PostgresSaver` stores conversation threads (`CHECKPOINTER=postgres`)
- **Redis** — pub/sub fan-out for WebSocket events across API instances

## Graph patterns

- **simple** — ReAct loop with shared tools (weather, news, vocabulary, GitHub, SQLite stub)
- **map_reduce** — parallel domain workers + synthesize step

See `examples/` for additional patterns: swarm, supervisor, plan-execute, email triage, RAG, etc.

## Project layout

```
src/agents/
  app.py              # FastAPI factory (CORS, lifespan, static files)
  settings.py         # pydantic-settings
  checkpointer.py     # Postgres/SQLite/memory lifecycle
  redis_client.py     # Redis pool
  ws/manager.py       # WebSocket + Redis pub/sub
  api/routers/        # health, agents, chat, ws
  graphs/daily.py     # LangGraph graphs
  static/             # built web assets
web/                  # Vite + TypeScript frontend
docker-compose.yml    # postgres + redis + api
```

## Production

```bash
cd web && npm run build
APP_ENV=production docker compose up --build -d
```

`APP_ENV=production` disables Swagger/OpenAPI.
