"""Shared LangGraph checkpointer lifecycle (Postgres, SQLite, or memory)."""

from __future__ import annotations

import sqlite3
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.sqlite import SqliteSaver
from psycopg import Connection
from psycopg.rows import dict_row

from agents.settings import Settings

_checkpointer: Any | None = None
_pg_conn: Connection | None = None
_sqlite_conn: sqlite3.Connection | None = None


def init_checkpointer(settings: Settings):
    """Create and configure the process-wide checkpointer."""
    global _checkpointer, _pg_conn, _sqlite_conn

    if settings.checkpointer == "postgres":
        _pg_conn = Connection.connect(
            settings.database_url,
            autocommit=True,
            row_factory=dict_row,
        )
        saver = PostgresSaver(_pg_conn)
        saver.setup()
        _checkpointer = saver
        return _checkpointer

    if settings.checkpointer == "sqlite":
        settings.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        _sqlite_conn = sqlite3.connect(str(settings.sqlite_path), check_same_thread=False)
        _checkpointer = SqliteSaver(_sqlite_conn)
        return _checkpointer

    _checkpointer = MemorySaver()
    return _checkpointer


def get_checkpointer():
    if _checkpointer is None:
        raise RuntimeError("Checkpointer not initialized — call init_checkpointer() at startup")
    return _checkpointer


def shutdown_checkpointer() -> None:
    global _checkpointer, _pg_conn, _sqlite_conn

    _checkpointer = None
    if _pg_conn is not None:
        _pg_conn.close()
        _pg_conn = None
    if _sqlite_conn is not None:
        _sqlite_conn.close()
        _sqlite_conn = None
