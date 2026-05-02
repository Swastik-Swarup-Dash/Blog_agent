# File: agent/nodes/writer.py
from __future__ import annotations

from typing import Any

from agent.gemini_client import get_model
from agent.state import GraphState

WRITER_SYSTEM_INSTRUCTION = (
    "You are an expert tech blogger writing for Dev.to. Tone: clear, "
    "insightful, slightly opinionated, never generic. Use concrete "
    "examples, real-world analogies, and code snippets where appropriate. "
    "Format in clean Markdown. Match the word target for each section. "
    "Total post target: 1800 to 2200 words."
)


def writer_node(state: GraphState) -> dict[str, Any]:
    model = get_model(use_search=False, system_instruction=WRITER_SYSTEM_INSTRUCTION)

    chosen_topic = state.get("chosen_topic", {})
    outline = state.get("outline", [])
    human_notes = (state.get("human_notes") or "").strip()
    rewrite_count = int(state.get("rewrite_count", 0))
    existing_draft = (state.get("draft") or "").strip()
    review_issues = state.get("review", {}).get("issues", []) if rewrite_count > 0 else []

    sections: list[str] = []
    previous_section = ""
    for section in outline:
        section_title = str(section.get("section_title", "Section"))
        word_target = int(section.get("word_target", 250))
        key_points = section.get("key_points", [])
        key_points_text = "\n".join(f"- {point}" for point in key_points)
        issue_text = "\n".join(f"- {issue}" for issue in review_issues) if review_issues else "None"
        notes_text = human_notes or "None"

        prompt = (
            f"Blog topic:\n{chosen_topic}\n\n"
            f"Write ONLY this section in Markdown.\n"
            f"Section title: {section_title}\n"
            f"Target words for this section: {word_target}\n"
            f"Key points to cover:\n{key_points_text}\n\n"
            f"Previous section text (for flow continuity):\n{previous_section or '(none)'}\n\n"
            f"Human editorial guidance:\n{notes_text}\n\n"
            f"Reviewer issues from prior pass (if any):\n{issue_text}\n\n"
            "Output section heading and body only."
        )

        response = model.generate_content(prompt)
        section_text = (response.text or "").strip()
        sections.append(section_text)
        previous_section = section_text

    new_draft = "\n\n".join(sections).strip()
    new_rewrite_count = rewrite_count + 1 if existing_draft else rewrite_count

    return {"draft": new_draft, "rewrite_count": new_rewrite_count}
