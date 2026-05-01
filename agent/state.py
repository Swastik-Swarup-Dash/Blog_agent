# File: agent/state.py
from __future__ import annotations

from typing import Any, TypedDict


class GraphState(TypedDict):
    topics: list[dict[str, Any]]
    chosen_topic: dict[str, Any]
    outline: list[dict[str, Any]]
    draft: str
    review: dict[str, Any]
    human_notes: str
    publish_result: dict[str, Any]
    rewrite_count: int
    run_id: str
