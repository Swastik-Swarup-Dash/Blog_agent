# File: cli.py
from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.tree import Tree

console = Console()
_current_topic_title = "Selected Topic"


def set_current_topic_title(title: str) -> None:
    global _current_topic_title
    _current_topic_title = title or "Selected Topic"


def handle_topic_approval(topics: list[dict[str, Any]]) -> dict[str, Any]:
    table = Table(header_style="bold cyan")
    table.add_column("Rank", style="bold")
    table.add_column("Score")
    table.add_column("Title")
    table.add_column("Summary")
    table.row_styles = ["none", "dim"]

    for idx, topic in enumerate(topics, start=1):
        table.add_row(
            str(idx),
            str(topic.get("score", "")),
            str(topic.get("title", "")),
            str(topic.get("summary", "")),
        )
    console.print(table)

    choice = Prompt.ask(
        "Enter number to select, type your own topic, or press Enter for top-ranked [1]",
        default="1",
    ).strip()

    chosen_topic: dict[str, Any]
    if choice.isdigit() and 1 <= int(choice) <= len(topics):
        chosen_topic = topics[int(choice) - 1]
    elif choice:
        chosen_topic = {"title": choice, "summary": "", "score": 0, "source_urls": []}
    else:
        chosen_topic = topics[0] if topics else {"title": "AI Trends", "summary": "", "score": 0, "source_urls": []}

    notes = Prompt.ask("Any notes for the outline? (Enter to skip)", default="")
    set_current_topic_title(str(chosen_topic.get("title", "Selected Topic")))
    return {"chosen_topic": chosen_topic, "human_notes": notes}


def handle_outline_approval(outline: list[dict[str, Any]]) -> dict[str, Any]:
    tree = Tree(f"[bold]{_current_topic_title}[/bold]")
    for section in outline:
        title = str(section.get("section_title", "Section"))
        word_target = int(section.get("word_target", 0))
        branch = tree.add(f"{title} ({word_target} words)")
        for point in section.get("key_points", []):
            branch.add(f"• {point}")
    console.print(tree)

    notes = Prompt.ask("Type edits or notes (Enter to approve as-is)", default="")
    return {"outline": outline, "human_notes": notes}


def handle_draft_approval(draft: str, review: dict[str, Any]) -> dict[str, Any]:
    score = review.get("score", 0)
    issues = review.get("issues", [])
    passed = bool(review.get("passed", False))
    border_color = "green" if passed else "red"
    issues_text = "\n".join(f"- {issue}" for issue in issues) if issues else "No issues."

    console.print(
        Panel(
            f"Score: {score}\nPassed: {passed}\n\nIssues:\n{issues_text}",
            title="Review Result",
            border_style=border_color,
        )
    )
    console.print(Markdown(draft))

    choice = Prompt.ask(
        "[A]pprove / [R]ewrite / [E]dit manually",
        choices=["A", "R", "E", "a", "r", "e"],
        default="A",
    ).upper()

    if choice == "R":
        notes = Prompt.ask("Describe what to change")
        return {"approved": False, "human_notes": notes}

    if choice == "E":
        draft_path = Path("/tmp/blog_draft.md")
        draft_path.write_text(draft, encoding="utf-8")
        editor = os.getenv("EDITOR", "vi")
        command = shlex.split(editor) + [str(draft_path)]
        subprocess.call(command)
        edited_text = draft_path.read_text(encoding="utf-8")
        return {"approved": True, "draft": edited_text, "human_notes": ""}

    return {"approved": True, "draft": draft, "human_notes": ""}
