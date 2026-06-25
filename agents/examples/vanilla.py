"""FastAPI service wrapping a LangGraph tool-calling agent.

Exposes a minimal chat API backed by Postgres checkpointing so conversations
persist across requests. The agent has a single ``search`` tool and follows the
standard LLM → tools loop.

Endpoints:

- ``POST /chat``          — send a message, get the final reply
- ``POST /chat/stream``   — SSE stream of per-node updates
- ``GET  /thread/{id}``   — inspect message history for a thread
- ``GET  /health``        — liveness check

Requires ``OPENAI_API_KEY`` and a running Postgres instance (``DATABASE_URL``).

Run::

    cd agents
    uv run uvicorn examples.vanilla:app --reload --host 127.0.0.1 --port 8000

Example request::

    curl -X POST http://127.0.0.1:8000/chat \\
      -H "Content-Type: application/json" \\
      -d '{"thread_id": "user-1", "message": "Search for LangGraph tutorials"}'
"""

import json
import os
import logging
from datetime import datetime
from typing import Literal
from contextlib import asynccontextmanager
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from psycopg import AsyncConnection
from psycopg.rows import dict_row
from pydantic import BaseModel

load_dotenv()


def get_logger():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


logger = get_logger()


def _serialize_message(message) -> dict:
    return {
        "type": message.__class__.__name__,
        "content": message.content or "",
    }


def _log_message(
    message: str,
    level: Literal["INFO", "WARNING", "ERROR", "CRITICAL"],
    **kwargs,
):
    logger.log(
        getattr(logging, level),
        json.dumps(
            {
                "message": message,
                "level": level,
                "timestamp": datetime.now().isoformat(),
                **kwargs,
            },
            default=str,
        ),
    )


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


@tool
def search(query: str) -> str:
    """Search the web."""
    _log_message("Searching the web", "INFO", query=query)
    return f"Results for {query}"


tools = [search]
llm = ChatOpenAI(model="gpt-4o").bind_tools(tools)


def call_llm(state):
    _log_message(
        "Calling LLM",
        "INFO",
        message_count=len(state["messages"]),
        messages=[_serialize_message(m) for m in state["messages"]],
    )
    return {"messages": [llm.invoke(state["messages"])]}


def should_continue(state):
    last = state["messages"][-1]
    return "tools" if getattr(last, "tool_calls", None) else END


def build_graph(checkpointer):
    graph = StateGraph(AgentState)
    graph.add_node("llm", call_llm)
    graph.add_node("tools", ToolNode(tools))
    graph.set_entry_point("llm")
    graph.add_conditional_edges("llm", should_continue)
    graph.add_edge("tools", "llm")
    return graph.compile(checkpointer=checkpointer)


def get_database_url() -> str:
    return os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost/postgres",
    )


graph = None
_db_conn: AsyncConnection | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global graph, _db_conn
    _db_conn = await AsyncConnection.connect(
        get_database_url(),
        autocommit=True,
        row_factory=dict_row,
    )
    checkpointer = AsyncPostgresSaver(_db_conn)
    await checkpointer.setup()
    graph = build_graph(checkpointer)
    yield
    await _db_conn.close()
    _db_conn = None


app = FastAPI(lifespan=lifespan)


class ChatRequest(BaseModel):
    thread_id: str
    message: str


class ChatResponse(BaseModel):
    thread_id: str
    response: str


class StateResponse(BaseModel):
    thread_id: str
    message_count: int
    messages: list[dict]


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    config = {"configurable": {"thread_id": req.thread_id}}
    try:
        result = await graph.ainvoke(
            {"messages": [HumanMessage(content=req.message)]},
            config=config,
        )
        return ChatResponse(
            thread_id=req.thread_id,
            response=result["messages"][-1].content,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/thread/{thread_id}", response_model=StateResponse)
async def get_thread(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    state = await graph.aget_state(config)
    if not state.values:
        raise HTTPException(status_code=404, detail="Thread not found")
    return StateResponse(
        thread_id=thread_id,
        message_count=len(state.values["messages"]),
        messages=[_serialize_message(m) for m in state.values["messages"]],
    )


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    config = {"configurable": {"thread_id": req.thread_id}}

    async def event_stream():
        async for step in graph.astream(
            {"messages": [HumanMessage(content=req.message)]},
            config=config,
            stream_mode="updates",
        ):
            for node, update in step.items():
                last = update["messages"][-1]
                payload = {
                    "node": node,
                    "message": _serialize_message(last),
                }
                yield f"data: {json.dumps(payload)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/health")
async def health():
    return {"status": "ok"}
