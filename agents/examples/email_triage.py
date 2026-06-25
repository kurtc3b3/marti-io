"""Human-in-the-loop email triage agent.

Fetches a batch of emails, classifies each as urgent, FYI, or spam, then routes
to the appropriate action. Urgent emails get an LLM-drafted reply that pauses for
human approval before sending. State is checkpointed so the graph can resume
after each interrupt.

Graph::

    fetch_emails ──► classify ──┬──► archive ──► next email
                                ├──► skip ─────► next email
                                └──► draft_reply ──► await_approval
                                                          ├──► send ──► next
                                                          └──► skip ──► next

Uses mock inbox/tools (no Gmail credentials required). Classification and
drafting call ``gpt-4o-mini`` with structured output.

Run::

    cd agents
    uv run python examples/email_triage.py          # interactive
    uv run python examples/email_triage.py --demo   # auto-approve sends

Programmatic usage::

    from examples.email_triage import app

    config = {"configurable": {"thread_id": "triage-1"}}
    app.invoke(
        {
            "messages": [],
            "emails": [],
            "current_index": 0,
            "processed": [],
            "human_decision": "",
        },
        config=config,
    )

    # Resume after human sets human_decision via update_state at interrupt
    state = app.get_state(config)
    if state.next and "await_approval" in state.next:
        app.update_state(config, {"human_decision": "send"})
        app.invoke(None, config=config)
"""

import copy
import json
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel

load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

MOCK_INBOX = [
    {
        "id": "1",
        "sender": "boss@company.com",
        "subject": "Q4 report due tomorrow",
        "body": "Please send the Q4 report by end of day tomorrow.",
        "category": "",
        "draft_reply": "",
        "action_taken": "",
    },
    {
        "id": "2",
        "sender": "newsletter@shop.com",
        "subject": "50% off sale this weekend",
        "body": "Limited time offer on all items. Unsubscribe at any time.",
        "category": "",
        "draft_reply": "",
        "action_taken": "",
    },
    {
        "id": "3",
        "sender": "hr@company.com",
        "subject": "Office closed Monday",
        "body": "The office will be closed Monday for maintenance. No action needed.",
        "category": "",
        "draft_reply": "",
        "action_taken": "",
    },
]


@tool
def fetch_unread_emails(max_results: int = 10) -> str:
    """Fetch unread emails from the inbox."""
    return json.dumps(MOCK_INBOX[:max_results])


@tool
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email reply."""
    return f"Email sent to {to} — subject: {subject}"


@tool
def archive_email(email_id: str) -> str:
    """Archive an email (remove from inbox)."""
    return f"Email {email_id} archived"


class Email(TypedDict):
    id: str
    subject: str
    sender: str
    body: str
    category: str
    draft_reply: str
    action_taken: str


class TriageState(TypedDict):
    messages: Annotated[list, add_messages]
    emails: list[Email]
    current_index: int
    processed: list[Email]
    human_decision: str


class Classification(BaseModel):
    category: str
    reason: str


def fetch_emails(state: TriageState):
    result = fetch_unread_emails.invoke({"max_results": 10})
    emails = json.loads(result)
    return {
        "emails": emails,
        "current_index": 0,
        "processed": [],
        "human_decision": "",
    }


def classify(state: TriageState):
    idx = state["current_index"]
    email = state["emails"][idx]

    result = llm.with_structured_output(Classification).invoke(
        [
            SystemMessage(
                content="""Classify emails as:
- urgent: needs a reply within 24h
- fyi: informational, no reply needed
- spam: unwanted or promotional"""
            ),
            HumanMessage(
                content=f"""From: {email['sender']}
Subject: {email['subject']}
Body: {email['body']}"""
            ),
        ]
    )

    updated_emails = state["emails"].copy()
    updated_emails[idx] = {**email, "category": result.category}
    return {"emails": updated_emails}


def draft_reply(state: TriageState):
    idx = state["current_index"]
    email = state["emails"][idx]

    draft = llm.invoke(
        [
            SystemMessage(content="Draft a professional, concise email reply."),
            HumanMessage(
                content=f"""From: {email['sender']}
Subject: {email['subject']}
Body: {email['body']}

Write only the reply body, no subject line needed."""
            ),
        ]
    )

    updated_emails = state["emails"].copy()
    updated_emails[idx] = {**email, "draft_reply": draft.content}
    return {"emails": updated_emails}


def await_approval(state: TriageState):
    return {}


def archive(state: TriageState):
    idx = state["current_index"]
    email = state["emails"][idx]

    archive_email.invoke({"email_id": email["id"]})

    updated_emails = state["emails"].copy()
    updated_emails[idx] = {**email, "action_taken": "archived"}
    processed = state["processed"] + [updated_emails[idx]]

    return {
        "emails": updated_emails,
        "processed": processed,
        "current_index": idx + 1,
        "human_decision": "",
    }


def send_reply(state: TriageState):
    idx = state["current_index"]
    email = state["emails"][idx]

    send_email.invoke(
        {
            "to": email["sender"],
            "subject": f"Re: {email['subject']}",
            "body": email["draft_reply"],
        }
    )

    updated_emails = state["emails"].copy()
    updated_emails[idx] = {**email, "action_taken": "sent"}
    processed = state["processed"] + [updated_emails[idx]]

    return {
        "emails": updated_emails,
        "processed": processed,
        "current_index": idx + 1,
        "human_decision": "",
    }


def skip(state: TriageState):
    idx = state["current_index"]
    email = state["emails"][idx]

    updated_emails = state["emails"].copy()
    updated_emails[idx] = {**email, "action_taken": "skipped"}
    processed = state["processed"] + [updated_emails[idx]]

    return {
        "emails": updated_emails,
        "processed": processed,
        "current_index": idx + 1,
        "human_decision": "",
    }


def route_after_classify(state: TriageState):
    category = state["emails"][state["current_index"]]["category"].lower()
    if category == "spam":
        return "archive"
    if category == "fyi":
        return "skip"
    return "draft_reply"


def route_after_approval(state: TriageState):
    if state.get("human_decision") == "send":
        return "send_reply"
    return "skip"


def route_next_email(state: TriageState):
    if state["current_index"] >= len(state["emails"]):
        return END
    return "classify"


def build_graph():
    graph = StateGraph(TriageState)

    graph.add_node("fetch_emails", fetch_emails)
    graph.add_node("classify", classify)
    graph.add_node("draft_reply", draft_reply)
    graph.add_node("await_approval", await_approval)
    graph.add_node("send_reply", send_reply)
    graph.add_node("archive", archive)
    graph.add_node("skip", skip)

    graph.set_entry_point("fetch_emails")
    graph.add_edge("fetch_emails", "classify")
    graph.add_conditional_edges(
        "classify",
        route_after_classify,
        {
            "archive": "archive",
            "skip": "skip",
            "draft_reply": "draft_reply",
        },
    )
    graph.add_edge("draft_reply", "await_approval")
    graph.add_conditional_edges(
        "await_approval",
        route_after_approval,
        {"send_reply": "send_reply", "skip": "skip"},
    )
    graph.add_conditional_edges("archive", route_next_email)
    graph.add_conditional_edges("skip", route_next_email)
    graph.add_conditional_edges("send_reply", route_next_email)

    return graph.compile(
        checkpointer=MemorySaver(),
        interrupt_before=["await_approval"],
    )


app = build_graph()


def _print_summary(config):
    processed = app.get_state(config).values["processed"]
    print(f"\nDone. Processed {len(processed)} emails:")
    for email in processed:
        print(f"  {email['action_taken'].upper():8} — {email['subject']}")


def run_demo():
    config = {"configurable": {"thread_id": "triage-demo"}}

    app.invoke(
        {
            "messages": [],
            "emails": [],
            "current_index": 0,
            "processed": [],
            "human_decision": "",
        },
        config=config,
    )

    while True:
        state = app.get_state(config)
        if not state.next:
            break

        if "await_approval" in state.next:
            idx = state.values["current_index"]
            email = state.values["emails"][idx]
            print(f"Auto-approving draft for: {email['subject']}")
            app.update_state(config, {"human_decision": "send"})

        app.invoke(None, config=config)

    _print_summary(config)


def run_triage():
    config = {"configurable": {"thread_id": "triage-session-1"}}

    print("Fetching emails...\n")
    app.invoke(
        {
            "messages": [],
            "emails": [],
            "current_index": 0,
            "processed": [],
            "human_decision": "",
        },
        config=config,
    )

    while True:
        state = app.get_state(config)
        if not state.next:
            break

        if "await_approval" not in state.next:
            app.invoke(None, config=config)
            continue

        idx = state.values["current_index"]
        emails = state.values["emails"]
        if idx >= len(emails):
            break

        email = emails[idx]
        print(f"\n{'=' * 50}")
        print(f"From:    {email['sender']}")
        print(f"Subject: {email['subject']}")
        print(f"Preview: {email['body'][:150]}...")
        print(f"\nDraft reply:\n{email['draft_reply']}")
        print(f"{'=' * 50}")

        decision = input("\n[s]end / [e]dit / [k]ip: ").strip().lower()
        updates: dict = {"human_decision": "skip"}

        if decision == "s":
            updates["human_decision"] = "send"
        elif decision == "e":
            new_body = input("New reply body:\n> ")
            updated = copy.deepcopy(emails)
            updated[idx]["draft_reply"] = new_body
            updates = {"emails": updated, "human_decision": "send"}

        app.update_state(config, updates)
        app.invoke(None, config=config)

    _print_summary(config)


if __name__ == "__main__":
    import sys

    if "--demo" in sys.argv:
        run_demo()
    else:
        run_triage()
