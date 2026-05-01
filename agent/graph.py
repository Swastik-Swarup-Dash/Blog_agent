# File: agent/graph.py
from __future__ import annotations

from typing import Any, Literal

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from agent.nodes.outline import outline_node
from agent.nodes.publisher import publisher_node
from agent.nodes.research import research_node
from agent.nodes.reviewer import reviewer_node
from agent.nodes.writer import writer_node
from agent.state import GraphState


def approve_topics_checkpoint(state: GraphState) -> dict[str, Any]:
    response = interrupt({"type": "approve_topics", "topics": state.get("topics", [])})
    if not isinstance(response, dict):
        raise ValueError("Topic approval response must be a dict.")
    return {
        "chosen_topic": response.get("chosen_topic", {}),
        "human_notes": str(response.get("human_notes", "")).strip(),
    }


def approve_outline_checkpoint(state: GraphState) -> dict[str, Any]:
    response = interrupt(
        {
            "type": "approve_outline",
            "chosen_topic": state.get("chosen_topic", {}),
            "outline": state.get("outline", []),
        }
    )
    if not isinstance(response, dict):
        raise ValueError("Outline approval response must be a dict.")
    updates: dict[str, Any] = {"outline": response.get("outline", state.get("outline", []))}
    if "human_notes" in response:
        updates["human_notes"] = str(response.get("human_notes", "")).strip()
    return updates


def approve_draft_checkpoint(state: GraphState) -> dict[str, Any]:
    response = interrupt(
        {
            "type": "approve_draft",
            "draft": state.get("draft", ""),
            "review": state.get("review", {}),
        }
    )
    if not isinstance(response, dict):
        raise ValueError("Draft approval response must be a dict.")

    approved = bool(response.get("approved", True))
    notes = str(response.get("human_notes", "")).strip()
    updates: dict[str, Any] = {}

    if "draft" in response:
        updates["draft"] = str(response["draft"])

    if approved:
        updates["human_notes"] = notes
    else:
        updates["human_notes"] = f"rewrite: {notes}".strip()

    return updates


def route_after_draft(state: GraphState) -> Literal["publisher_node", "writer_node"]:
    if int(state.get("rewrite_count", 0)) >= 2:
        return "publisher_node"
    notes = (state.get("human_notes") or "").lower()
    if "rewrite" in notes:
        return "writer_node"
    return "publisher_node"


def compile_graph(checkpointer: Any):
    builder = StateGraph(GraphState)
    builder.add_node("research_node", research_node)
    builder.add_node("approve_topics", approve_topics_checkpoint)
    builder.add_node("outline_node", outline_node)
    builder.add_node("approve_outline", approve_outline_checkpoint)
    builder.add_node("writer_node", writer_node)
    builder.add_node("reviewer_node", reviewer_node)
    builder.add_node("approve_draft", approve_draft_checkpoint)
    builder.add_node("publisher_node", publisher_node)

    builder.add_edge(START, "research_node")
    builder.add_edge("research_node", "approve_topics")
    builder.add_edge("approve_topics", "outline_node")
    builder.add_edge("outline_node", "approve_outline")
    builder.add_edge("approve_outline", "writer_node")
    builder.add_edge("writer_node", "reviewer_node")
    builder.add_edge("reviewer_node", "approve_draft")
    builder.add_conditional_edges(
        "approve_draft",
        route_after_draft,
        {"publisher_node": "publisher_node", "writer_node": "writer_node"},
    )
    builder.add_edge("publisher_node", END)

    return builder.compile(checkpointer=checkpointer)
