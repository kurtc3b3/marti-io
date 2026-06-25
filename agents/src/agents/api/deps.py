"""FastAPI dependencies."""

from __future__ import annotations

from agents.graphs.daily import GraphKind, get_graph
from agents.settings import Settings, get_settings


def settings_dep() -> Settings:
    return get_settings()


def graph_dep(kind: GraphKind = "simple"):
    settings = get_settings()

    def _get():
        return get_graph(kind, settings)

    return _get
