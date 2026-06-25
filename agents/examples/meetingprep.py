"""Meeting prep agent with parallel attendee research.

Fetches the next calendar meeting, researches each attendee in parallel via
``Send``, pulls relevant email threads, writes a markdown briefing, and saves it
to a mock document. Uses mock calendar, Gmail, search, and Drive tools — no
Google credentials required.

Graph::

    fetch_meeting ──► research_attendee (×N, parallel) ──► fetch_emails
                                                            ──► write_briefing
                                                            ──► save_to_drive
                                                            ──► END

Parallel branches merge attendee research with ``operator.add`` on the
``research`` state field.

Run::

    cd agents
    uv run python examples/meetingprep.py

Programmatic usage::

    from examples.meetingprep import app

    config = {"configurable": {"thread_id": "meeting-prep-1"}}
    result = app.invoke(
        {
            "meeting_id": "",
            "meeting_title": "",
            "meeting_time": "",
            "meeting_duration": 0,
            "attendees": [],
            "research": [],
            "email_threads": [],
            "briefing": "",
            "drive_doc_url": "",
        },
        config=config,
    )
    print(result["briefing"])
"""

import json
import operator
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.types import Send
from pydantic import BaseModel

load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

MOCK_MEETING = {
    "id": "evt-1",
    "title": "Q4 Planning with Acme Corp",
    "time": "2026-06-22T14:00:00Z",
    "duration": 60,
    "attendees": [
        {"name": "Jane Smith", "email": "jane@acme.com", "company": "Acme Corp"},
        {"name": "Bob Lee", "email": "bob@acme.com", "company": "Acme Corp"},
        {"name": "Me", "email": "me@example.com", "company": ""},
    ],
}

MOCK_EMAIL_THREADS = [
    {
        "subject": "Re: Q4 planning agenda",
        "participants": "jane@acme.com",
        "message_count": 4,
        "snippet": "Thanks for sending the draft agenda. We should focus on revenue targets and hiring plan.",
    },
    {
        "subject": "Acme partnership update",
        "participants": "bob@acme.com",
        "message_count": 2,
        "snippet": "Sharing the latest metrics before our sync on Monday.",
    },
]

MOCK_PEOPLE = {
    "jane smith": {
        "role": "VP Sales",
        "company": "Acme Corp",
        "news": "Jane Smith recently led Acme Corp's expansion into the EU market.",
        "talking_points": [
            "EU launch results",
            "Pipeline for Q4",
            "Enterprise deal cycle length",
        ],
    },
    "bob lee": {
        "role": "Head of Product",
        "company": "Acme Corp",
        "news": "Bob Lee published a blog post on Acme's new analytics platform.",
        "talking_points": [
            "Analytics roadmap",
            "Integration priorities",
            "Customer feedback themes",
        ],
    },
}


@tool
def fetch_next_meeting() -> str:
    """Fetch the next upcoming meeting from the calendar."""
    return json.dumps(MOCK_MEETING)


@tool
def search_email_threads(query: str, max_results: int = 5) -> str:
    """Search for email threads matching a query."""
    _ = query
    return json.dumps(MOCK_EMAIL_THREADS[:max_results])


@tool
def search_person(name: str, company: str) -> str:
    """Search for recent news and info about a person."""
    key = name.lower()
    if key in MOCK_PEOPLE:
        person = MOCK_PEOPLE[key]
        return f"{person['news']} ({company or person['company']})"
    return f"Recent info about {name} at {company}: no major public updates found."


@tool
def create_drive_doc(title: str, content: str) -> str:
    """Create a document with the given content."""
    slug = title.lower().replace(" ", "-")[:40]
    _ = content
    return f"https://docs.example.com/document/{slug}"


class AttendeeResearch(TypedDict):
    name: str
    email: str
    role: str
    company: str
    recent_news: str
    talking_points: list[str]


class MeetingPrepState(TypedDict, total=False):
    meeting_id: str
    meeting_title: str
    meeting_time: str
    meeting_duration: int
    attendees: list[dict]
    current_attendee: dict
    research: Annotated[list[AttendeeResearch], operator.add]
    email_threads: list[dict]
    briefing: str
    drive_doc_url: str


class AttendeeInfo(BaseModel):
    role: str
    company: str
    talking_points: list[str]


def fetch_meeting(state: MeetingPrepState):
    _ = state
    meeting = json.loads(fetch_next_meeting.invoke({}))
    return {
        "meeting_id": meeting["id"],
        "meeting_title": meeting["title"],
        "meeting_time": meeting["time"],
        "meeting_duration": meeting["duration"],
        "attendees": meeting["attendees"],
        "research": [],
    }


def research_attendee(state: MeetingPrepState):
    attendee = state["current_attendee"]
    company = attendee.get("company", "")

    search_result = search_person.invoke(
        {"name": attendee["name"], "company": company}
    )

    info = llm.with_structured_output(AttendeeInfo).invoke(
        [
            SystemMessage(
                content="Extract professional info about this person from search results."
            ),
            HumanMessage(
                content=f"""Person: {attendee['name']} ({attendee['email']})
Search results: {search_result}

Infer their role, company, and 3 relevant talking points for a meeting."""
            ),
        ]
    )

    return {
        "research": [
            {
                "name": attendee["name"],
                "email": attendee["email"],
                "role": info.role,
                "company": info.company,
                "recent_news": search_result,
                "talking_points": info.talking_points,
            }
        ]
    }


def fetch_emails(state: MeetingPrepState):
    attendee_names = [a["name"] for a in state["attendees"] if a["name"]]
    query = f"from:({' OR '.join(attendee_names)}) subject:{state['meeting_title']}"
    result = search_email_threads.invoke({"query": query, "max_results": 5})
    threads = json.loads(result)
    return {"email_threads": threads}


def write_briefing(state: MeetingPrepState):
    research_summary = "\n\n".join(
        [
            f"**{r['name']}** ({r['role']} at {r['company']})\n"
            f"Recent news: {r['recent_news'][:200]}\n"
            f"Talking points: {', '.join(r['talking_points'])}"
            for r in state["research"]
        ]
    )

    email_summary = "\n".join(
        [
            f"- {t['subject']} ({t['message_count']} messages): {t['snippet']}"
            for t in state["email_threads"]
        ]
    )

    briefing = llm.invoke(
        [
            SystemMessage(
                content="You are an executive assistant. Write a concise meeting briefing in markdown."
            ),
            HumanMessage(
                content=f"""Meeting: {state['meeting_title']}
Time: {state['meeting_time']} ({state['meeting_duration']} mins)

ATTENDEE RESEARCH:
{research_summary}

RECENT EMAIL THREADS:
{email_summary}

Write a briefing with:
1. Meeting objective (inferred)
2. Attendee profiles (1 paragraph each)
3. Recent context from emails
4. Suggested agenda
5. Key talking points"""
            ),
        ]
    )

    return {"briefing": briefing.content}


def save_to_drive(state: MeetingPrepState):
    url = create_drive_doc.invoke(
        {
            "title": f"Meeting Prep: {state['meeting_title']} — {state['meeting_time'][:10]}",
            "content": state["briefing"],
        }
    )
    return {"drive_doc_url": url}


def fan_out_to_attendees(state: MeetingPrepState):
    return [
        Send("research_attendee", {**state, "current_attendee": attendee})
        for attendee in state["attendees"]
        if attendee["email"] != "me@example.com"
    ]


def build_graph():
    graph = StateGraph(MeetingPrepState)

    graph.add_node("fetch_meeting", fetch_meeting)
    graph.add_node("research_attendee", research_attendee)
    graph.add_node("fetch_emails", fetch_emails)
    graph.add_node("write_briefing", write_briefing)
    graph.add_node("save_to_drive", save_to_drive)

    graph.set_entry_point("fetch_meeting")
    graph.add_conditional_edges("fetch_meeting", fan_out_to_attendees)
    graph.add_edge("research_attendee", "fetch_emails")
    graph.add_edge("fetch_emails", "write_briefing")
    graph.add_edge("write_briefing", "save_to_drive")
    graph.add_edge("save_to_drive", END)

    return graph.compile(checkpointer=MemorySaver())


app = build_graph()


def run():
    config = {"configurable": {"thread_id": "meeting-prep-1"}}

    print("Fetching your next meeting...\n")

    for step in app.stream(
        {
            "meeting_id": "",
            "meeting_title": "",
            "meeting_time": "",
            "meeting_duration": 0,
            "attendees": [],
            "research": [],
            "email_threads": [],
            "briefing": "",
            "drive_doc_url": "",
        },
        config=config,
        stream_mode="updates",
    ):
        for node, update in step.items():
            if node == "fetch_meeting":
                print(f"Meeting: {update['meeting_title']} at {update['meeting_time']}")
                print(f"Attendees: {[a['name'] for a in update['attendees']]}\n")

            elif node == "research_attendee":
                person = update["research"][0]
                print(
                    f"Researched: {person['name']} — {person['role']} at {person['company']}"
                )

            elif node == "fetch_emails":
                print(f"\nFound {len(update['email_threads'])} relevant email threads")

            elif node == "write_briefing":
                print("\nWriting briefing doc...")

            elif node == "save_to_drive":
                print(f"\nBriefing saved: {update['drive_doc_url']}")
                print("\n--- Briefing preview ---")
                final = app.get_state(config).values
                print(final["briefing"][:500] + "...")


if __name__ == "__main__":
    run()
