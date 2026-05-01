# File: agent/nodes/reviewer.py
from __future__ import annotations

import json
from typing import Any

from agent.gemini_client import get_model
from agent.state import GraphState

REVIEWER_SYSTEM_INSTRUCTION = (
    "You are a senior technical editor and fact-checker. Review the blog "
    "post draft and return ONLY valid JSON with these keys: "
    "score (int 0-100), issues (list of str describing specific problems), "
    "passed (bool, true if score >= 75). Check: factual consistency, "
    "clarity, logical flow, no hallucinated statistics, SEO-friendly "
    "headings, strong opening hook, no filler sentences."
)


def reviewer_node(state: GraphState) -> dict[str, Any]:
    model = get_model(use_search=False, system_instruction=REVIEWER_SYSTEM_INSTRUCTION)
    draft = state.get("draft", "")
    rewrite_count = int(state.get("rewrite_count", 0))
    existing_notes = (state.get("human_notes") or "").strip()

    response = model.generate_content(
        f"Review this blog draft:\n\n{draft}",
        generation_config={"response_mime_type": "application/json"},
    )

    parsed = json.loads(response.text or "{}")
    review = {
        "score": int(parsed.get("score", 0)),
        "issues": [str(i) for i in parsed.get("issues", []) if isinstance(i, str)],
        "passed": bool(parsed.get("passed", False)),
    }

    notes = existing_notes
    if not review["passed"] and rewrite_count < 2 and review["issues"]:
        issue_lines = "\n".join(f"- {issue}" for issue in review["issues"])
        auto_block = f"rewrite: address reviewer issues\n{issue_lines}"
        notes = f"{existing_notes}\n\n{auto_block}".strip() if existing_notes else auto_block

    return {"review": review, "human_notes": notes}
