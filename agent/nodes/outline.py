# File: agent/nodes/outline.py
from __future__ import annotations

import json
from typing import Any

from agent.gemini_client import get_model
from agent.state import GraphState


def _parse_outline(text: str) -> list[dict[str, Any]]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Try stripping markdown if present
        cleaned_text = text.strip()
        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text[7:]
        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text[:-3]
        data = json.loads(cleaned_text.strip())

    if isinstance(data, dict):
        # Sometimes models wrap the array in a dict like {"outline": [...]} or {"items": [...]}
        for key, val in data.items():
            if isinstance(val, list):
                data = val
                break

    if not isinstance(data, list):
        raise ValueError("Outline response must be a JSON list.")
    outline: list[dict[str, Any]] = []
    for section in data:
        if not isinstance(section, dict):
            continue
        outline.append(
            {
                "section_title": str(section.get("section_title", "")).strip(),
                "word_target": int(section.get("word_target", 0)),
                "key_points": [str(k) for k in section.get("key_points", []) if isinstance(k, str)],
            }
        )
    return outline


def outline_node(state: GraphState) -> dict[str, Any]:
    chosen_topic = state.get("chosen_topic", {})
    human_notes = (state.get("human_notes") or "").strip()

    notes_line = (
        f"The human reviewer left these notes: {human_notes}. Apply them."
        if human_notes
        else "No additional human notes."
    )
    prompt = (
        "Create a 5-7 section outline for a 2000-word developer-focused Dev.to blog post.\n"
        "Mandatory sections:\n"
        "1) Introduction (hook + thesis)\n"
        "2) Conclusion (takeaways + CTA)\n"
        "Return only JSON array where each item has:\n"
        "- section_title (str)\n"
        "- word_target (int)\n"
        "- key_points (list[str])\n\n"
        f"Topic:\n{json.dumps(chosen_topic, ensure_ascii=False)}\n\n"
        f"{notes_line}"
    )

    model = get_model(use_search=False)
    response = model.generate_content(
        prompt,
        generation_config={
            "response_mime_type": "application/json",
            "response_schema": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["section_title", "word_target", "key_points"],
                    "properties": {
                        "section_title": {"type": "string"},
                        "word_target": {"type": "integer"},
                        "key_points": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
        },
    )
    outline = _parse_outline(response.text or "[]")
    return {"outline": outline}
