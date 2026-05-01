# File: agent/nodes/research.py
from __future__ import annotations

import json
import time
from typing import Any

from agent.gemini_client import get_model
from agent.state import GraphState

RESEARCH_SYSTEM_INSTRUCTION = (
    "You are a tech research analyst. Using live Google Search, find the "
    "8 to 10 most compelling and novel technology stories from the past "
    "7 days that would make excellent 2000-word Dev.to blog posts for "
    "developers and AI practitioners. Focus: AI breakthroughs, LLM "
    "releases, GPU architecture, open-source models, agent frameworks, "
    "inference optimization, multimodal AI. Return ONLY valid JSON — "
    "a list of objects with keys: title (str), summary (str, 2 sentences), "
    "score (int 1-10), source_urls (list of str). No markdown, no "
    "preamble, no explanation."
)


def _parse_json_list(text: str) -> list[dict[str, Any]]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()
    parsed = json.loads(cleaned)
    if not isinstance(parsed, list):
        raise ValueError("Research response must be a JSON list.")
    normalized: list[dict[str, Any]] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "title": str(item.get("title", "")).strip(),
                "summary": str(item.get("summary", "")).strip(),
                "score": int(item.get("score", 0)),
                "source_urls": [str(u) for u in item.get("source_urls", []) if isinstance(u, str)],
            }
        )
    return normalized


def research_node(state: GraphState) -> dict[str, Any]:
    model = get_model(use_search=True, system_instruction=RESEARCH_SYSTEM_INSTRUCTION)
    prompt = "Return the requested JSON list now."

    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            response = model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"},
            )
            topics = _parse_json_list(response.text or "")
            topics = sorted(topics, key=lambda x: x.get("score", 0), reverse=True)
            return {"topics": topics[:10]}
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt < 3:
                time.sleep(2 ** (attempt - 1))
            else:
                break

    raise RuntimeError(f"research_node failed after 3 retries: {last_error}") from last_error
