"""Subgraph pattern: nest a specialized agent inside a parent graph.

The outer graph handles the user conversation; the inner research subgraph runs
search → summarize as a self-contained unit. The parent invokes the compiled
subgraph from a node and bridges the summary back into ``messages``.

Graph::

    research (subgraph) ──► write ──► END

Inner research subgraph::

    search ──► summarize ──► END

Weather queries use ``get_weather`` (wttr.in); other queries use the mock
``search`` tool.

Run::

    cd agents
    uv run python examples/subgraphs.py

Programmatic usage::

    from langchain_core.messages import HumanMessage
    from examples.subgraphs import app

    result = app.invoke(
        {"messages": [HumanMessage(content="What is the weather in Paris?")]}
    )
    print(result["messages"][-1].content)
"""

from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from tools.search import search
from tools.weather import get_weather

load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


class ResearchState(TypedDict):
    query: str
    results: list[str]
    summary: str


class MainState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


def search_node(state: ResearchState):
    query = state["query"]
    if "weather" in query.lower():
        city = "Paris" if "paris" in query.lower() else query.split()[-1].rstrip("?")
        result = get_weather.invoke({"city": city})
    else:
        result = search.invoke({"query": query})
    return {"results": [result]}


def summarize_node(state: ResearchState):
    context = "\n".join(state["results"])
    response = llm.invoke(
        f"Summarize these findings in 1-2 sentences:\n{context}"
    )
    return {"summary": response.content}


research_graph = StateGraph(ResearchState)
research_graph.add_node("search", search_node)
research_graph.add_node("summarize", summarize_node)
research_graph.set_entry_point("search")
research_graph.add_edge("search", "summarize")
research_graph.add_edge("summarize", END)
research_agent = research_graph.compile()


def research_node(state: MainState):
    result = research_agent.invoke(
        {
            "query": state["messages"][-1].content,
            "results": [],
            "summary": "",
        }
    )
    return {"messages": [AIMessage(content=result["summary"])]}


def write_node(state: MainState):
    research = state["messages"][-1].content
    response = llm.invoke(
        f"Write a concise, helpful answer for the user based on this research:\n{research}"
    )
    return {"messages": [AIMessage(content=response.content)]}


main_graph = StateGraph(MainState)
main_graph.add_node("research", research_node)
main_graph.add_node("write", write_node)
main_graph.set_entry_point("research")
main_graph.add_edge("research", "write")
main_graph.add_edge("write", END)

app = main_graph.compile()


if __name__ == "__main__":
    result = app.invoke(
        {"messages": [HumanMessage(content="What is the weather in Paris?")]}
    )
    print(result["messages"][-1].content)
