"""Map-reduce pattern: fan out work in parallel, then synthesize.

Demonstrates LangGraph's ``Send`` API for dynamic fan-out. One worker branch
runs per topic, results are merged via ``operator.add`` on the ``results`` field,
and a reduce node combines everything into a final summary.

Graph::

    split ──► worker (×N, parallel) ──► reduce ──► END

In a real application the worker would call an LLM or tools per topic; the
reduce step would synthesize with another LLM call.

Run::

    cd agents
    uv run python examples/mapreduce.py

Programmatic usage::

    from examples.mapreduce import app

    result = app.invoke({
        "topics": ["AI trends", "climate change", "global economy"],
        "results": [],
        "final": "",
    })
    print(result["final"])
"""

from langgraph.graph import StateGraph, END
from langgraph.types import Send
from typing import TypedDict, Annotated
import operator


class MapReduceState(TypedDict):
    topics: list[str]          # input: list of things to research
    results: Annotated[list, operator.add]  # output: collected in parallel
    final: str


# Fan-out: spawn one worker per topic
def split(state):
    # Send() dynamically creates parallel branches
    return [
        Send("worker", {"topic": topic, "results": [], "final": ""})
        for topic in state["topics"]
    ]


# Each worker runs independently
def worker(state):
    topic = state["topic"]
    result = f"Research on {topic}: [findings]"  # real: call LLM/tools
    return {"results": [result]}


# Collect all results and synthesize
def reduce(state):
    combined = "\n".join(state["results"])
    summary = f"Summary of all research:\n{combined}"  # real: call LLM
    return {"final": summary}


graph = StateGraph(MapReduceState)
graph.add_node("worker", worker)
graph.add_node("reduce", reduce)
graph.set_conditional_entry_point(split)        # fan out from start
graph.add_edge("worker", "reduce")              # workers converge here
graph.add_edge("reduce", END)

app = graph.compile()


if __name__ == "__main__":
    result = app.invoke({
        "topics": ["AI trends", "climate change", "global economy"],
        "results": [],
        "final": "",
    })
    print(result["final"])
