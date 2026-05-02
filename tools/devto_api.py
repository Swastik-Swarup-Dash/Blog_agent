# File: tools/devto_api.py
from __future__ import annotations

import os
from typing import Any

import requests


class DevToAPIError(Exception):
    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


class DevToClient:
    BASE_URL = "https://dev.to/api"

    def __init__(self, token: str | None = None) -> None:
        self.token = token or os.getenv("DEVTO_TOKEN")
        if not self.token:
            raise ValueError("Missing Dev.to token. Set DEVTO_TOKEN in the environment.")
        self.headers = {
            "api-key": self.token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _handle_response(self, response: requests.Response) -> dict[str, Any]:
        if not (200 <= response.status_code < 300):
            try:
                payload = response.json()
                message = str(payload.get("error", response.text))
            except Exception:  # noqa: BLE001
                message = response.text
            raise DevToAPIError(message=message, status_code=response.status_code)
        try:
            return response.json()
        except ValueError as exc:
            raise DevToAPIError("Invalid JSON response from Dev.to API.", response.status_code) from exc

    def get_user(self) -> dict[str, Any]:
        url = f"{self.BASE_URL}/users/me"
        try:
            response = requests.get(url, headers=self.headers, timeout=20)
            data = self._handle_response(response)
            return {
                "id": data.get("id"),
                "username": data.get("username"),
                "url": f"https://dev.to/{data.get('username')}",
            }
        except requests.RequestException as exc:
            raise DevToAPIError(f"Failed to fetch Dev.to user: {exc}", 0) from exc

    def create_post(
        self,
        title: str,
        content: str,
        tags: list[str],
        publish_status: str,
    ) -> dict[str, Any]:
        url = f"{self.BASE_URL}/articles"
        payload = {
            "article": {
                "title": title,
                "body_markdown": content,
                "published": publish_status == "public",
                "tags": tags[:4],
            }
        }
        try:
            response = requests.post(url, headers=self.headers, json=payload, timeout=30)
            data = self._handle_response(response)
            return {"id": data.get("id"), "url": data.get("url"), "publishedAt": data.get("published_at")}
        except requests.RequestException as exc:
            raise DevToAPIError(f"Failed to create Dev.to post: {exc}", 0) from exc
