"""Self-critique loop: generate, score, and revise until quality is met.

A generator node drafts a response, a critic node scores it 0–10 with
structured feedback, and the graph loops back to the generator when the score
is below 8. A hard cap of three iterations prevents runaway revisions.

Graph::

    generate ──► critique ──(score < 8?)──► generate
                         └──► END

The critic injects its feedback as a new ``HumanMessage`` so the generator
sees concrete improvement instructions on each pass.

Run::

    cd agents
    uv run python examples/selfcritique.py

Programmatic usage::

    from langchain_core.messages import HumanMessage
    from examples.selfcritique import app

    result = app.invoke({
        "messages": [HumanMessage(content="Write a short story about a cat.")],
        "iterations": 0,
        "quality_score": 0,
    })
    print(result["messages"][-1].content)
"""

from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from dotenv import load_dotenv
from pydantic import BaseModel


load_dotenv()


class CritiqueResult(BaseModel):
    score: int
    feedback: str


class ReflectionState(TypedDict):
    messages: Annotated[list, add_messages]
    iterations: int
    quality_score: int  # 0-10


llm = ChatOpenAI(model="gpt-4o")


def generate(state):
    response = llm.invoke(state["messages"])
    return {"messages": [response], "iterations": state["iterations"] + 1}


def critique(state):
    last_output = state["messages"][-1].content

    critique_prompt = f"""Rate this response 0-10 and explain issues:

    Response: {last_output}

    Return JSON: {{"score": 7, "feedback": "needs more detail on X"}}"""

    result = llm.with_structured_output(CritiqueResult).invoke(critique_prompt)

    # Inject feedback as a new human message so generator sees it
    feedback_msg = HumanMessage(content=f"Improve this. Feedback: {result.feedback}")
    return {
        "messages": [feedback_msg],
        "quality_score": result.score
    }


def should_revise(state):
    if state["quality_score"] >= 8:
        return END
    if state["iterations"] >= 3:      # hard cap — avoid infinite loops
        return END
    return "generate"


graph = StateGraph(ReflectionState)
graph.add_node("generate", generate)
graph.add_node("critique", critique)
graph.set_entry_point("generate")
graph.add_edge("generate", "critique")
graph.add_conditional_edges(
    "critique",
    should_revise,
    {
        "generate": "generate",
        END: END,
    },
)

app = graph.compile()


if __name__ == "__main__":
    result = app.invoke({
        "messages": [HumanMessage(content="Write a short story about a cat.")],
        "iterations": 0,
        "quality_score": 0,
    })
    print(result["messages"][-1].content)
