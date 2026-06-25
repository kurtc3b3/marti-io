"""LangGraph swarm handoff helper.

Provides ``create_handoff_tool`` for multi-agent swarms. When an agent hands off
mid-turn, any sibling tool calls from the same AI message get skipped
``ToolMessage`` responses so OpenAI's chat history stays valid.

Used by ``examples/swarm.py``. Each handoff tool returns a ``Command`` that
jumps to another agent in the parent graph and updates ``active_agent``.

Run the swarm demo that uses this module::

    cd agents
    uv run python examples/swarm.py

Programmatic usage::

    from handoff import create_handoff_tool

    transfer_to_writer = create_handoff_tool(agent_name="writer")
    print(transfer_to_writer.name)  # transfer_to_writer
"""

from __future__ import annotations

import re
from typing import Annotated, Any

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import BaseTool, InjectedToolCallId, tool
from langgraph.prebuilt import InjectedState
from langgraph.types import Command

WHITESPACE_RE = re.compile(r"\s+")
METADATA_KEY_HANDOFF_DESTINATION = "__handoff_destination"


def _normalize_agent_name(agent_name: str) -> str:
    return WHITESPACE_RE.sub("_", agent_name.strip()).lower()


def _get_messages(state: Any) -> list:
    if isinstance(state, dict):
        return state["messages"]
    return state.messages


def _pending_tool_messages(
    messages: list,
    *,
    handoff_tool_call_id: str,
    handoff_tool_name: str,
    agent_name: str,
) -> list[ToolMessage]:
    """Resolve every open tool call in the latest AI turn before handing off."""
    answered_ids = {
        message.tool_call_id
        for message in messages
        if isinstance(message, ToolMessage)
    }
    last_ai = next(
        (message for message in reversed(messages) if isinstance(message, AIMessage)),
        None,
    )
    if not last_ai or not last_ai.tool_calls:
        return [
            ToolMessage(
                content=f"Successfully transferred to {agent_name}",
                name=handoff_tool_name,
                tool_call_id=handoff_tool_call_id,
            )
        ]

    tool_messages: list[ToolMessage] = []
    for tool_call in last_ai.tool_calls:
        tool_call_id = tool_call["id"]
        if tool_call_id in answered_ids:
            continue
        if tool_call_id == handoff_tool_call_id:
            content = f"Successfully transferred to {agent_name}"
        else:
            content = (
                "Skipped because the conversation was transferred to another agent."
            )
        tool_messages.append(
            ToolMessage(
                content=content,
                name=tool_call["name"],
                tool_call_id=tool_call_id,
            )
        )
    return tool_messages


def create_handoff_tool(
    *,
    agent_name: str,
    name: str | None = None,
    description: str | None = None,
) -> BaseTool:
    if name is None:
        name = f"transfer_to_{_normalize_agent_name(agent_name)}"

    if description is None:
        description = f"Ask agent '{agent_name}' for help"

    @tool(name, description=description)
    def handoff_to_agent(
        state: Annotated[Any, InjectedState],
        tool_call_id: Annotated[str, InjectedToolCallId],
    ) -> Command:
        tool_messages = _pending_tool_messages(
            _get_messages(state),
            handoff_tool_call_id=tool_call_id,
            handoff_tool_name=name,
            agent_name=agent_name,
        )
        return Command(
            goto=agent_name,
            graph=Command.PARENT,
            update={
                "messages": [*_get_messages(state), *tool_messages],
                "active_agent": agent_name,
            },
        )

    handoff_to_agent.metadata = {METADATA_KEY_HANDOFF_DESTINATION: agent_name}
    return handoff_to_agent


if __name__ == "__main__":
    for agent in ("researcher", "analyst", "writer"):
        handoff = create_handoff_tool(agent_name=agent)
        print(f"{handoff.name}: {handoff.description}")
