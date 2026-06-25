"""Minimal LangGraph agent with a single weather tool.

A hand-rolled tool-calling loop without ``ToolNode``: the LLM node decides
whether to call ``get_weather``, the tool node executes it, and control returns
to the LLM for a natural-language answer. Weather data comes from wttr.in.

Graph::

    llm ──(tool calls?)──► tool ──► llm ──► END

Run::

    cd agents
    uv run python examples/weather.py
"""

from dotenv import load_dotenv

from typing import Annotated
from typing_extensions import TypedDict

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph, add_messages

import json
from urllib.parse import quote
from urllib.request import urlopen
from langchain_core.tools import tool


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


tools = [get_weather]
tools_by_name = {tool.name: tool for tool in tools}
llm_with_tools = llm.bind_tools(tools)


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    tool_calls: int


def call_llm(state: AgentState):
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}


def run_tool(state: AgentState):
    last = state["messages"][-1]
    results = []
    for tool_call in last.tool_calls:
        tool = tools_by_name[tool_call["name"]]
        content = tool.invoke(tool_call["args"])
        results.append(
            ToolMessage(content=str(content), tool_call_id=tool_call["id"])
        )
    return {"messages": results, "tool_calls": state["tool_calls"] + len(results)}


def should_continue(state):
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and last.tool_calls:
        return "tool"
    return END


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("llm", call_llm)
    graph.add_node("tool", run_tool)
    graph.add_edge("tool", "llm")
    graph.add_conditional_edges("llm", should_continue)
    graph.set_entry_point("llm")

    app = graph.compile()
    return app


if __name__ == "__main__":
    app = build_graph()
    result = app.invoke(
        {
            "messages": [HumanMessage(content="What's the weather in SF?")],
            "tool_calls": 0,
        }
    )

    print(result["messages"][-1].content)
