"""Plan-and-execute pattern: plan steps, run them, replan on failure.

A planner node breaks a goal into short steps, an executor runs each step in
order, and a replanner revises the plan when a step fails. Replans are capped at
two to avoid infinite loops. Weather steps call ``get_weather`` (wttr.in).

Graph::

    planner ──► executor ──(more steps?)──► executor ──► END
                    └──(failed?)──► replanner ──► executor

Run::

    cd agents
    uv run python examples/planexecute.py

Programmatic usage::

    from examples.planexecute import app

    result = app.invoke({
        "goal": "Get the weather of Paris.",
        "plan": [],
        "completed": [],
        "current_step": "",
        "failed": False,
        "replans": 0,
    })
    for item in result["completed"]:
        print(item)
"""

from typing import TypedDict

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
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


class Plan(BaseModel):
    steps: list[str]


class PlanExecuteState(TypedDict):
    goal: str
    plan: list[str]
    completed: list[str]
    current_step: str
    failed: bool
    replans: int


def planner(state):
    plan = llm.with_structured_output(Plan).invoke(
        f"Create a short step-by-step plan to: {state['goal']}. "
        "Prefer 1-2 concrete steps."
    )
    return {
        "plan": plan.steps,
        "completed": [],
        "current_step": "",
        "failed": False,
        "replans": 0,
    }


def executor(state):
    step = state["plan"][0]
    try:
        if "paris" in step.lower() or "weather" in step.lower():
            result = get_weather.invoke({"city": "Paris"})
        else:
            result = f"Completed: {step}"
        return {
            "plan": state["plan"][1:],
            "completed": state["completed"] + [f"{step}: {result}"],
            "current_step": step,
            "failed": False,
        }
    except Exception as exc:
        return {
            "current_step": step,
            "failed": True,
            "completed": state["completed"] + [f"{step}: ERROR {exc}"],
        }


def replanner(state):
    context = "\n".join(state["completed"])
    new_plan = llm.with_structured_output(Plan).invoke(
        f"""Original goal: {state['goal']}
Completed so far:
{context}
Step '{state['current_step']}' failed. Create a revised plan with at most 2 steps."""
    )
    return {
        "plan": new_plan.steps,
        "failed": False,
        "replans": state["replans"] + 1,
    }


def route_executor(state):
    if state["failed"]:
        if state["replans"] >= 2:
            return END
        return "replanner"
    if not state["plan"]:
        return END
    return "executor"


graph = StateGraph(PlanExecuteState)
graph.add_node("planner", planner)
graph.add_node("executor", executor)
graph.add_node("replanner", replanner)
graph.set_entry_point("planner")
graph.add_edge("planner", "executor")
graph.add_conditional_edges("executor", route_executor)
graph.add_edge("replanner", "executor")

app = graph.compile()


if __name__ == "__main__":
    result = app.invoke(
        {
            "goal": "Get the weather of Paris.",
            "plan": [],
            "completed": [],
            "current_step": "",
            "failed": False,
            "replans": 0,
        }
    )

    print(f"Goal: {result['goal']}\n")
    for item in result["completed"]:
        print(f"- {item}")
