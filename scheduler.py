# File: scheduler.py
from __future__ import annotations

import json
import os
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import requests
from dotenv import load_dotenv
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command
from rich.console import Console
from rich.panel import Panel

from agent.graph import compile_graph
from agent.state import GraphState
from cli import (
    handle_draft_approval,
    handle_outline_approval,
    handle_topic_approval,
    set_current_topic_title,
)

console = Console()


def _log_run(entry: dict[str, Any]) -> None:
    with Path("runs.log").open("a", encoding="utf-8") as file:
        file.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _notify_slack_error(message: str) -> None:
    webhook = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook:
        return
    try:
        requests.post(webhook, json={"text": message}, timeout=10).raise_for_status()
    except requests.RequestException:
        pass


def _extract_interrupt_payload(result: Any) -> dict[str, Any] | None:
    if not isinstance(result, dict):
        return None
    interrupts = result.get("__interrupt__")
    if not interrupts:
        return None
    first = interrupts[0] if isinstance(interrupts, (list, tuple)) else interrupts
    payload = getattr(first, "value", first)
    return payload if isinstance(payload, dict) else None


def _stream_until_pause_or_end(graph: Any, current_input: Any, config: dict[str, Any]) -> dict[str, Any]:
    latest_event: dict[str, Any] = {}
    for event in graph.stream(current_input, config=config, stream_mode="updates"):
        if isinstance(event, dict):
            latest_event = event
            if "__interrupt__" in event:
                return event
    state_snapshot = graph.get_state(config)
    return dict(state_snapshot.values) if state_snapshot and state_snapshot.values else latest_event


def run() -> None:
    load_dotenv()
    run_id = str(uuid4())
    start_time = datetime.now(UTC)

    initial_state: GraphState = {
        "topics": [],
        "chosen_topic": {},
        "outline": [],
        "draft": "",
        "review": {},
        "human_notes": "",
        "publish_result": {},
        "rewrite_count": 0,
        "run_id": run_id,
    }

    console.print(Panel(f"Dev.to Blog Agent — Run {run_id}", style="bold cyan"))

    with SqliteSaver.from_conn_string("checkpoints.db") as checkpointer:
        graph = compile_graph(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": run_id}}

        current_input: Any = initial_state
        while True:
            result = _stream_until_pause_or_end(graph, current_input, config)
            interrupt_payload = _extract_interrupt_payload(result)

            if not interrupt_payload:
                final_state = graph.get_state(config).values
                end_time = datetime.now(UTC)
                entry = {
                    "run_id": run_id,
                    "topic": final_state.get("chosen_topic", {}).get("title", ""),
                    "published_url": final_state.get("publish_result", {}).get("url", ""),
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration": str(end_time - start_time),
                }
                _log_run(entry)
                console.print(
                    Panel(
                        f"Completed.\nURL: {entry['published_url']}",
                        title="Run Complete",
                        style="green",
                    )
                )
                return

            event_type = interrupt_payload.get("type")
            if event_type == "approve_topics":
                human_response = handle_topic_approval(interrupt_payload.get("topics", []))
                set_current_topic_title(str(human_response.get("chosen_topic", {}).get("title", "Selected Topic")))
            elif event_type == "approve_outline":
                set_current_topic_title(str(interrupt_payload.get("chosen_topic", {}).get("title", "Selected Topic")))
                human_response = handle_outline_approval(interrupt_payload.get("outline", []))
            elif event_type == "approve_draft":
                human_response = handle_draft_approval(
                    interrupt_payload.get("draft", ""),
                    interrupt_payload.get("review", {}),
                )
            else:
                raise RuntimeError(f"Unknown interrupt type: {event_type}")

            current_input = Command(resume=human_response)


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:  # noqa: BLE001
        error_time = datetime.now(UTC).isoformat()
        message = f"Dev.to agent failed at {error_time}: {exc}"
        _log_run(
            {
                "run_id": "unknown",
                "topic": "",
                "published_url": "",
                "start_time": error_time,
                "end_time": error_time,
                "duration": "0:00:00",
                "error": f"{exc}\n{traceback.format_exc()}",
            }
        )
        _notify_slack_error(message)
        raise
