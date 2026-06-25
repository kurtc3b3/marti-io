"""Multi-tool LangGraph agent with persistent conversation memory.

Demonstrates a classic ReAct-style loop: the LLM decides which tools to call,
``ToolNode`` executes them, and results flow back until the model produces a
final answer. Three tools are available: weather lookup, web search, and a
calculator.

Graph::

    llm ──(tool calls?)──► tools ──► llm ──► END

Checkpoint backends (pass to ``build_graph`` or set ``CHECKPOINTER`` env var):

- ``memory``   — in-process ``MemorySaver`` (default)
- ``sqlite``   — persists to ``checkpoints.db``
- ``postgres`` — persists to ``DATABASE_URL``

Run the demo::

    cd agents
    uv run python examples/multi_tools.py

The demo uses a fresh ``thread_id`` so follow-up questions share context within
the same run. Set ``CHECKPOINTER=postgres`` to exercise Postgres persistence.

Programmatic usage::

    import uuid
    from langchain_core.messages import HumanMessage
    from examples.multi_tools import build_graph

    thread_id = f"demo-{uuid.uuid4()}"
    app = build_graph(memory_type="memory")
    config = {"configurable": {"thread_id": thread_id}}

    result = app.invoke(
        {"messages": [HumanMessage(content="What's the weather in SF?")]},
        config=config,
    )
    print(result["messages"][-1].content)

Stream node updates as they complete::

    for step in app.stream(
        {"messages": [HumanMessage(content="What's the bitcoin price?")]},
        config=config,
        stream_mode="updates",
    ):
        node_name = list(step.keys())[0]
        messages = step[node_name]["messages"]
        print(f"\\n[{node_name}]")
        for msg in messages:
            print(f"  {msg.__class__.__name__}: {msg.content or msg.tool_calls}")

Inspect thread state::

    state = app.get_state(config)

    print(state.values)    # full AgentState dict
    print(state.next)      # next node(s) to run; empty when done
    print(state.metadata)  # step count, run id, etc.

    for msg in state.values["messages"]:
        print(f"[{msg.__class__.__name__}] {msg.content}")

Browse checkpoint history and resume from a past step::

    for checkpoint in app.get_state_history(config):
        print(f"Step {checkpoint.metadata['step']} — next: {checkpoint.next}")
        print(f"  Messages: {len(checkpoint.values['messages'])}")

    history = list(app.get_state_history(config))
    past_checkpoint = history[-3]  # third from oldest
    result = app.invoke(None, past_checkpoint.config)
"""

import os
import json
from urllib.request import urlopen
from urllib.parse import quote

from dotenv import load_dotenv

from typing import TypedDict, Annotated, Literal
from langgraph.graph.message import add_messages
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode
from langgraph.graph import END
from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver

from langchain_core.tools import tool


load_dotenv()


@tool
def search(query: str) -> str:
    """Search the web for current information."""
    # In real life: use Tavily, SerpAPI, etc.
    query_lower = query.lower()
    results = {
        "bitcoin": "Bitcoin is trading at $67,000 USD.",
        "france gdp": "France GDP is approximately $2.78 trillion USD in 2023.",
        "gdp of france": "France GDP is approximately $2.78 trillion USD in 2023.",
    }
    for key, value in results.items():
        if key in query_lower:
            return value
    return f"No results found for: {query}"


@tool
def calculator(expression: str) -> str:
    """Evaluate a math expression. Example: '25 * 4 + 10'"""
    try:
        result = eval(expression, {"__builtins__": {}})
        return str(result)
    except Exception as e:
        return f"Error: {e}"


@tool
def get_weather(city: str) -> str:
    """Get the current weather for a city."""
    url = f"https://wttr.in/{quote(city)}?format=j1"
    with urlopen(url, timeout=10) as response:
        data = json.load(response)
    current = data["current_condition"][0]
    description = current["weatherDesc"][0]["value"]
    temp_f = current["temp_F"]
    return f"{city}: {current['temp_C']}°C ({temp_f}°F), {description}"


tools = [get_weather, search, calculator]

# Node 2: Execute tool calls
# ToolNode handles this automatically — it:
# - reads tool_calls from the last AI message
# - runs the matching tool
# - wraps results in ToolMessage objects
tool_node = ToolNode(tools)

# Bind tools to the LLM so it knows what's available
llm = ChatOpenAI(model="gpt-4o").bind_tools(tools)


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


def repair_messages(messages: list[BaseMessage]) -> list[BaseMessage]:
    """Fill missing ToolMessages left by interrupted or partial runs."""
    answered_ids = {
        message.tool_call_id
        for message in messages
        if isinstance(message, ToolMessage)
    }
    repaired: list[BaseMessage] = []

    for message in messages:
        repaired.append(message)
        if not isinstance(message, AIMessage) or not message.tool_calls:
            continue

        for tool_call in message.tool_calls:
            tool_call_id = tool_call["id"]
            if tool_call_id in answered_ids:
                continue
            repaired.append(
                ToolMessage(
                    content="Skipped: prior tool call did not complete.",
                    name=tool_call["name"],
                    tool_call_id=tool_call_id,
                )
            )
            answered_ids.add(tool_call_id)

    return repaired


# Node 1: Call the LLM
def call_llm(state: AgentState):
    messages = repair_messages(state["messages"])
    response = llm.invoke(messages)
    return {"messages": [response]}


def should_continue(state: AgentState) -> str:
    last_message = state["messages"][-1]

    # If the LLM made tool calls, route to the tool node
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"

    # Otherwise, we're done
    return END


def build_graph(memory_type: Literal["memory", "sqlite", "postgres"] = "memory"):
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("llm", call_llm)
    graph.add_node("tools", tool_node)

    # Set where the graph starts
    graph.set_entry_point("llm")

    # After LLM: conditionally go to tools or END
    graph.add_conditional_edges(
        "llm",
        should_continue,
        {
            "tools": "tools",  # route label → node name
            END: END
        }
    )

    # After tools: always go back to LLM
    graph.add_edge("tools", "llm")

    if memory_type == "memory":
        checkpointer = MemorySaver()
    elif memory_type == "sqlite":
        import sqlite3

        from langgraph.checkpoint.sqlite import SqliteSaver

        conn = sqlite3.connect("checkpoints.db", check_same_thread=False)
        checkpointer = SqliteSaver(conn)
    elif memory_type == "postgres":
        import psycopg
        from langgraph.checkpoint.postgres import PostgresSaver
        from psycopg.rows import dict_row

        db_uri = os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost/postgres",
        )
        conn = psycopg.connect(db_uri, autocommit=True, row_factory=dict_row)
        checkpointer = PostgresSaver(conn)
        checkpointer.setup()
    else:
        raise ValueError(f"Invalid memory type: {memory_type}")

    app = graph.compile(checkpointer=checkpointer)
    return app


def run(
    question: str,
    thread_id: str,
    memory_type: Literal["memory", "sqlite", "postgres"] = "memory",
):
    print(f"\n🧠 Question: {question}\n")

    config = {"configurable": {"thread_id": thread_id}}
    app = build_graph(memory_type=memory_type)

    return app.invoke(
        {"messages": [HumanMessage(content=question)]},
        config=config,
    )


if __name__ == "__main__":
    import uuid

    thread_id = f"demo-{uuid.uuid4()}"
    memory_type = os.getenv("CHECKPOINTER", "memory")

    result = run("What's the weather in SF?", thread_id, memory_type=memory_type)
    print(result["messages"][-1].content)

    result = run("What is that temperature times 3?", thread_id, memory_type=memory_type)
    print(result["messages"][-1].content)
