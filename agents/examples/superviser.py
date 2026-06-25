"""Supervisor pattern: a router LLM delegates work to specialist agents.

A supervisor node reads the conversation and routes to one of three workers —
researcher, analyst, or writer — until the task is complete. Workers with tools
loop through a shared ``ToolNode`` before returning to the supervisor. Step
limits and a ``writer_done`` flag prevent infinite routing loops.

Graph::

    supervisor ──► researcher ──► tools ──► supervisor
              ├──► analyst    ──► tools ──► supervisor
              ├──► writer     ─────────────► supervisor
              └──► FINISH

Workers::

    researcher  — web search
    analyst     — calculator
    writer      — final answer synthesis

Run::

    cd agents
    uv run python examples/superviser.py

The demo streams supervisor routing decisions and worker output to stdout.

Programmatic usage::

    from examples.superviser import app
    from langchain_core.messages import HumanMessage

    import uuid

    config = {
        "configurable": {"thread_id": f"supervisor-{uuid.uuid4()}"},
        "recursion_limit": 25,
    }
    result = app.invoke(
        {
            "messages": [HumanMessage(content="What is the GDP of France?")],
            "steps": 0,
            "writer_done": False,
        },
        config=config,
    )
    print(result["messages"][-1].content)
"""

import uuid
from typing import Annotated, Literal, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel

load_dotenv()

MAX_SUPERVISOR_STEPS = 12


@tool
def search(query: str) -> str:
    """Search the web for current information."""
    query_lower = query.lower()
    if "population" in query_lower and "france" in query_lower:
        return "France population is approximately 68 million in 2023."
    results = {
        "france gdp": "France GDP is approximately $2.78 trillion USD in 2023.",
        "gdp of france": "France GDP is approximately $2.78 trillion USD in 2023.",
        "gdp france": "France GDP is approximately $2.78 trillion USD in 2023.",
        "france population": "France population is approximately 68 million in 2023.",
    }
    for key, value in results.items():
        if key in query_lower:
            return value
    return f"No results found for: {query}"


@tool
def calculate(expression: str) -> str:
    """Run a math calculation."""
    try:
        return str(eval(expression, {"__builtins__": {}}))
    except Exception as exc:
        return f"Error: {exc}"


llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


def make_worker(system_prompt: str, tools: list):
    agent_llm = llm.bind_tools(tools) if tools else llm

    def worker(state):
        messages = [SystemMessage(content=system_prompt)] + state["messages"]
        response = agent_llm.invoke(messages)
        return {"messages": [response]}

    return worker


researcher = make_worker(
    "You are a research specialist. Use search to find accurate information.",
    tools=[search],
)

analyst = make_worker(
    "You are a data analyst. Use the calculator for any numerical work.",
    tools=[calculate],
)


def writer(state):
    messages = [
        SystemMessage(
            content=(
                "You are a writer. Synthesize the conversation into one clear, "
                "complete final answer for the user."
            )
        ),
        *state["messages"],
    ]
    response = llm.invoke(messages)
    return {"messages": [response], "writer_done": True}


class RouteDecision(BaseModel):
    next: Literal["researcher", "analyst", "writer", "FINISH"]
    reason: str


supervisor_llm = llm.with_structured_output(RouteDecision)

SUPERVISOR_PROMPT = """You are a supervisor managing these workers:
- researcher: finds information via web search
- analyst: does math and data analysis
- writer: writes the final answer

Given the conversation, decide who should act next.

Rules:
- Send to analyst after researcher has found the needed facts.
- Send to writer once facts and any calculations are available.
- Return FINISH after the writer has produced a complete answer.
- Do not loop back to researcher if usable data is already in the conversation."""


class SupervisorState(TypedDict):
    messages: Annotated[list, add_messages]
    next: str
    reason: str
    steps: int
    writer_done: bool


def supervisor(state):
    steps = state.get("steps", 0) + 1

    if state.get("writer_done"):
        return {
            "next": "FINISH",
            "reason": "Writer already produced the final answer.",
            "steps": steps,
        }

    if steps >= MAX_SUPERVISOR_STEPS:
        return {
            "next": "FINISH",
            "reason": "Reached the supervisor step limit.",
            "steps": steps,
        }

    recent = state["messages"][-8:]
    decision = supervisor_llm.invoke(
        [SystemMessage(content=SUPERVISOR_PROMPT), *recent]
    )
    return {
        "next": decision.next,
        "reason": decision.reason,
        "steps": steps,
    }


def route_worker(state):
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and last.tool_calls:
        return "tools"
    return "supervisor"


graph = StateGraph(SupervisorState)

graph.add_node("supervisor", supervisor)
graph.add_node("researcher", researcher)
graph.add_node("analyst", analyst)
graph.add_node("writer", writer)
graph.add_node("tools", ToolNode([search, calculate]))

graph.set_entry_point("supervisor")
graph.add_conditional_edges(
    "supervisor",
    lambda state: state["next"],
    {
        "researcher": "researcher",
        "analyst": "analyst",
        "writer": "writer",
        "FINISH": END,
    },
)
graph.add_conditional_edges("researcher", route_worker)
graph.add_conditional_edges("analyst", route_worker)
graph.add_edge("tools", "supervisor")
graph.add_edge("writer", "supervisor")

app = graph.compile(checkpointer=MemorySaver())


def run_supervisor(question: str):
    config = {
        "configurable": {"thread_id": f"supervisor-{uuid.uuid4()}"},
        "recursion_limit": 25,
    }

    for step in app.stream(
        {
            "messages": [HumanMessage(content=question)],
            "steps": 0,
            "writer_done": False,
        },
        config=config,
        stream_mode="updates",
    ):
        for node, update in step.items():
            if node == "supervisor":
                print(f"\nSupervisor -> {update['next']} ({update['reason']})")
            elif "messages" in update:
                last = update["messages"][-1]
                preview = last.content[:100] if last.content else "(tool call)"
                print(f"[{node}]: {preview}")


if __name__ == "__main__":
    run_supervisor(
        "What is the GDP of France, and what is that divided by its population of 68 million?"
    )
