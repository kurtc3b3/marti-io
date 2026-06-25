"""Multi-agent swarm with peer-to-peer handoffs.

Three ReAct agents — researcher, analyst, and writer — collaborate on a task.
Each agent can call its own tools and hand off to another agent via
``create_handoff_tool`` from ``handoff``. Handoffs resolve any pending
tool calls in the same turn so OpenAI's chat history stays valid.

Agents::

    researcher  — search; hands off to analyst or writer
    analyst     — calculator; hands off to writer or researcher
    writer      — synthesizes the final answer

The swarm starts with ``researcher`` as the active agent. Conversation state is
checkpointed in memory so a ``thread_id`` can carry context across invocations.

Run::

    cd agents
    uv run python examples/swarm.py

Programmatic usage::

    import uuid
    from langchain_core.messages import HumanMessage
    from examples.swarm import app_swarm

    config = {"configurable": {"thread_id": f"swarm-{uuid.uuid4()}"}}
    result = app_swarm.invoke(
        {"messages": [HumanMessage(content="What is the GDP of France?")]},
        config=config,
    )
    print(result["messages"][-1].content)
"""

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from langgraph_swarm import create_swarm

from handoff import create_handoff_tool
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


llm = ChatOpenAI(model="gpt-4o")

researcher_agent = create_react_agent(
    llm,
    tools=[
        search,
        create_handoff_tool(agent_name="analyst"),
        create_handoff_tool(agent_name="writer"),
    ],
    prompt=(
        "You research information using search. "
        "Finish tool calls before handing off. "
        "Never call search and a handoff tool in the same turn. "
        "Hand off to analyst for math, or writer for the final answer."
    ),
    name="researcher",
)

analyst_agent = create_react_agent(
    llm,
    tools=[
        calculator,
        create_handoff_tool(agent_name="writer"),
        create_handoff_tool(agent_name="researcher"),
    ],
    prompt=(
        "You analyze data with the calculator. "
        "Finish tool calls before handing off. "
        "Never call calculator and a handoff tool in the same turn. "
        "Hand off to writer when done."
    ),
    name="analyst",
)

writer_agent = create_react_agent(
    llm,
    tools=[
        create_handoff_tool(agent_name="researcher"),
        create_handoff_tool(agent_name="analyst"),
    ],
    prompt="You write final answers. Only hand off if you need more information.",
    name="writer",
)

workflow = create_swarm(
    [researcher_agent, analyst_agent, writer_agent],
    default_active_agent="researcher",
)
app_swarm = workflow.compile(checkpointer=MemorySaver())


def run_swarm(question: str, thread_id: str = "swarm-1"):
    config = {"configurable": {"thread_id": thread_id}}
    result = app_swarm.invoke(
        {"messages": [HumanMessage(content=question)]},
        config=config,
    )
    return result


if __name__ == "__main__":
    import uuid

    thread_id = f"swarm-{uuid.uuid4()}"
    result = run_swarm(
        "What is the GDP of France, and what is that divided by its population of 68 million?",
        thread_id=thread_id,
    )
    print(result["messages"][-1].content)
