import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


class QwenClient:
    def __init__(self):
        self.base_url = os.getenv(
            "QWEN_BASE_URL",
            "http://localhost:8000/v1",
        )
        self.model = os.getenv(
            "QWEN_MODEL",
            "Qwen/Qwen3-14B",
        )
        self.api_key = os.getenv(
            "QWEN_API_KEY",
            "EMPTY",
        )

        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
        )

    def chat(
        self,
        messages: list[dict[str, Any]],
        temperature: float = 0.2,
        max_tokens: int = 2000,
        tools: list[dict[str, Any]] | None = None,
    ):
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if tools:
            kwargs["tools"] = tools

        return self.client.chat.completions.create(**kwargs)
