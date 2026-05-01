# File: agent/gemini_client.py
from __future__ import annotations

import os

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))


def get_model(use_search: bool = False, system_instruction: str | None = None) -> genai.GenerativeModel:
    tools = [{"google_search": {}}] if use_search else []
    return genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        tools=tools,
        system_instruction=system_instruction,
    )
