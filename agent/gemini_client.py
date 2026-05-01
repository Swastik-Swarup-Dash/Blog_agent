# File: agent/gemini_client.py
from __future__ import annotations

import os

from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

class GeminiModelWrapper:
    def __init__(self, use_search: bool, system_instruction: str | None) -> None:
        self.client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        self.model_name = "gemini-2.5-flash"
        
        tools = [{"google_search": {}}] if use_search else []
        self.config = types.GenerateContentConfig(
            tools=tools,
            system_instruction=system_instruction,
        )

    def generate_content(
        self,
        prompt: str,
        generation_config: dict | None = None
    ):
        config = self.config
        if generation_config:
            # Overwrite properties from the passed dict
            if "response_mime_type" in generation_config:
                config.response_mime_type = generation_config["response_mime_type"]
        
        return self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=config
        )


def get_model(
    use_search: bool = False,
    system_instruction: str | None = None,
) -> GeminiModelWrapper:
    return GeminiModelWrapper(use_search, system_instruction)
