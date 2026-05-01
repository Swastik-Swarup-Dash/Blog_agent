# File: agent/gemini_client.py
from __future__ import annotations

import os
import json
from groq import Groq
from dotenv import load_dotenv

try:
    from ddgs import DDGS
except ImportError:
    DDGS = None

load_dotenv()

class FakeResponse:
    def __init__(self, text: str):
        self.text = text

class GeminiModelWrapper:
    def __init__(self, use_search: bool, system_instruction: str | None) -> None:
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        # Using Llama 3.3 70B via Groq
        self.model_name = "llama-3.3-70b-versatile"
        self.use_search = use_search
        self.system_instruction = system_instruction or ""

    def generate_content(
        self,
        prompt: str,
        generation_config: dict | None = None
    ) -> FakeResponse:
        messages = []
        
        # Determine format
        response_format = {"type": "text"}
        if generation_config and generation_config.get("response_mime_type") == "application/json":
            response_format = {"type": "json_object"}
            
        sys_prompt = self.system_instruction
        if response_format["type"] == "json_object":
             sys_prompt += "\nOutput raw JSON only."
             prompt += "\nReturn JSON."
             
        if self.use_search and DDGS:
            # We'll just grab some recent news for context
            try:
                results = DDGS().news("Tech artificial intelligence LLM news", max_results=5)
                context = json.dumps(results, indent=2)
                sys_prompt += f"\n\nHere are some recent news articles you can use for research:\n{context}\n"
            except Exception as e:
                pass # search failed, just ignore
                
        if sys_prompt:
            messages.append({"role": "system", "content": sys_prompt})
            
        messages.append({"role": "user", "content": prompt})

        chat_completion = self.client.chat.completions.create(
            messages=messages,
            model=self.model_name,
            temperature=0.7,
            response_format=response_format
        )
        return FakeResponse(chat_completion.choices[0].message.content)

def get_model(
    use_search: bool = False,
    system_instruction: str | None = None,
) -> GeminiModelWrapper:
    return GeminiModelWrapper(use_search, system_instruction)
