"""Safety gate pattern: check requests before running the agent.

Every user message passes through a structured safety check first. Safe
requests reach a tool-calling agent; unsafe ones get a rejection message without
calling tools or the main LLM workflow.

Graph::

    gate ──(safe?)──► agent ──(tool calls?)──► tool ──► agent ──► END
         └──► reject ──► END

The gate uses ``with_structured_output`` to return a boolean and reason. The
agent path uses ``get_weather`` (wttr.in) as a minimal tool-calling example.

Run::

    cd agents
    uv run python examples/gate.py

Programmatic usage::

    from langchain_core.messages import HumanMessage
    from examples.gate import app

    result = app.invoke({
        "messages": [HumanMessage(content="What is the weather in Paris?")],
        "safe": False,
        "rejection_reason": "",
    })
    print(result["messages"][-1].content)
"""

from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel

from langchain_core.tools import tool
import json
from urllib.parse import quote
from urllib.request import urlopen

load_dotenv()


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


llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
llm_with_tools = llm.bind_tools([get_weather])
tools_by_name = {get_weather.name: get_weather}


class GateState(TypedDict):
    messages: Annotated[list, add_messages]
    safe: bool
    rejection_reason: str


class SafetyCheck(BaseModel):
    safe: bool
    reason: str


def gate(state):
    last = state["messages"][-1].content
    check = llm.with_structured_output(SafetyCheck).invoke(
        f"Is this request safe and appropriate? Request: {last}"
    )
    return {"safe": check.safe, "rejection_reason": check.reason}


def reject(state):
    msg = AIMessage(content=f"I can't help with that. {state['rejection_reason']}")
    return {"messages": [msg]}


def call_llm(state):
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}


def run_tool(state):
    last = state["messages"][-1]
    results = []
    for tool_call in last.tool_calls:
        tool = tools_by_name[tool_call["name"]]
        content = tool.invoke(tool_call["args"])
        results.append(
            ToolMessage(content=str(content), tool_call_id=tool_call["id"])
        )
    return {"messages": results}


def route_gate(state):
    return "agent" if state["safe"] else "reject"


def route_agent(state):
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and last.tool_calls:
        return "tool"
    return END


graph = StateGraph(GateState)
graph.add_node("gate", gate)
graph.add_node("agent", call_llm)
graph.add_node("tool", run_tool)
graph.add_node("reject", reject)
graph.set_entry_point("gate")
graph.add_conditional_edges("gate", route_gate)
graph.add_conditional_edges("agent", route_agent)
graph.add_edge("tool", "agent")
graph.add_edge("reject", END)

app = graph.compile()


if __name__ == "__main__":
    result = app.invoke(
        {
            "messages": [HumanMessage(content="What is the weather in Paris?")],
            "safe": False,
            "rejection_reason": "",
        }
    )
    print(result["messages"][-1].content)
