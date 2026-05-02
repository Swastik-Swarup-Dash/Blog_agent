# File: agent/gemini_client.py
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv
from groq import Groq

load_dotenv()


@dataclass
class GroqResponse:
    text: str


class GroqModelWrapper:
    def __init__(self, model_name: str, system_instruction: str | None) -> None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("Missing GROQ_API_KEY in environment.")
        self.client = Groq(api_key=api_key)
        self.model_name = model_name
        self.system_instruction = system_instruction

    def generate_content(self, prompt: str, generation_config: dict | None = None) -> GroqResponse:
        messages = []
        if self.system_instruction:
            messages.append({"role": "system", "content": self.system_instruction})
        messages.append({"role": "user", "content": prompt})

        temperature = None
        max_tokens = None
        if generation_config:
            if "temperature" in generation_config:
                temperature = generation_config["temperature"]
            if "max_output_tokens" in generation_config:
                max_tokens = generation_config["max_output_tokens"]

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content if response.choices else ""
        return GroqResponse(text=content or "")


def get_model(use_search: bool = False, system_instruction: str | None = None) -> GroqModelWrapper:
    model_name = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")
    if use_search:
        search_notice = "Do not claim to have performed live web searches. Use general knowledge only."
        if system_instruction:
            system_instruction = f"{system_instruction}\n\n{search_notice}"
        else:
            system_instruction = search_notice
    return GroqModelWrapper(model_name=model_name, system_instruction=system_instruction)
