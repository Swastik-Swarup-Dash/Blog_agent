# File: agent/nodes/publisher.py
from __future__ import annotations

import json
import os
import smtplib
from email.message import EmailMessage
from typing import Any

import requests

from agent.gemini_client import get_model
from agent.state import GraphState
from tools.devto_api import DevToClient


def _generate_tags(title: str) -> list[str]:
    model = get_model(use_search=False)
    prompt = (
        f"Given this tech blog topic: {title}. Return exactly 4 "
        "relevant Dev.to tags as a JSON list of strings. Tags must be "
        "lowercase, single words or hyphenated. No explanation."
    )
    response = model.generate_content(
        prompt,
        generation_config={"response_mime_type": "application/json"},
    )
    
    raw_text = (response.text or "").strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.startswith("json"):
            raw_text = raw_text[4:].strip()
    if not raw_text:
        raw_text = "[]"
    parsed = json.loads(raw_text)
    if not isinstance(parsed, list):
        raise ValueError("Tag generation did not return a JSON list.")

    tags: list[str] = []
    for item in parsed:
        if not isinstance(item, str):
            continue
        tag = item.strip().lower().replace(" ", "")
        tag = "".join(ch for ch in tag if ch.isalnum())
        if tag and tag not in tags:
            tags.append(tag)
    if len(tags) < 4:
        fallback = [w.strip(".,!?").lower() for w in title.split() if len(w) > 2]
        for word in fallback:
            normalized = word.replace(" ", "")
            normalized = "".join(ch for ch in normalized if ch.isalnum())
            if normalized and normalized not in tags:
                tags.append(normalized)
            if len(tags) >= 4:
                break
    return tags[:4]


def _notify_slack(url: str, title: str) -> None:
    webhook = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook:
        return
    try:
        response = requests.post(
            webhook,
            json={"text": f"Published: {url} ({title})"},
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"Slack notification failed: {exc}") from exc


def _notify_email(url: str, title: str) -> None:
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    recipient = os.getenv("NOTIFY_EMAIL")
    if not all([host, user, password, recipient]):
        return

    msg = EmailMessage()
    msg["Subject"] = f"Blog published: {title}"
    msg["From"] = user
    msg["To"] = recipient
    msg.set_content(f"Your Dev.to blog is live:\n{url}")

    try:
        with smtplib.SMTP(host, port, timeout=20) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(msg)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Email notification failed: {exc}") from exc


def publisher_node(state: GraphState) -> dict[str, Any]:
    chosen_topic = state.get("chosen_topic", {})
    title = str(chosen_topic.get("title", "Untitled Post"))
    draft = state.get("draft", "")

    tags = _generate_tags(title)
    client = DevToClient()
    result = client.create_post(
        title=title,
        content=draft,
        tags=tags,
        publish_status="public",
    )

    publish_result = {
        "url": result.get("url", ""),
        "published_at": result.get("publishedAt", ""),
        "devto_id": result.get("id", ""),
    }

    _notify_slack(publish_result["url"], title)
    _notify_email(publish_result["url"], title)

    return {"publish_result": publish_result}
