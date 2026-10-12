import logging
import os
from typing import Any

from dotenv import load_dotenv
from openai import APIConnectionError, APITimeoutError, OpenAI

load_dotenv()
logger = logging.getLogger(__name__)


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
        timeout_sec = float(os.getenv("QWEN_TIMEOUT", "180.0"))

        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=timeout_sec,
        )

    def chat(
        self,
        messages: list[dict[str, Any]],
        temperature: float = 0.2,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
    ):
        tokens_limit = max_tokens or int(os.getenv("QWEN_MAX_TOKENS", "1500"))
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": tokens_limit,
        }

        if tools:
            kwargs["tools"] = tools

        try:
            response = self.client.chat.completions.create(**kwargs)
            if not response.choices:
                raise ValueError("Model returned an empty choices list.")
            return response
        except APITimeoutError as exc:
            logger.error("Timeout connecting to local model at %s (timeout=%ss)", self.base_url, exc)
            raise TimeoutError(f"Model request timed out after connecting to {self.base_url}") from exc
        except APIConnectionError as exc:
            logger.error("Connection failed to local model endpoint at %s", self.base_url)
            raise ConnectionError(f"Unable to reach local model endpoint at {self.base_url}. Please ensure Ollama is running.") from exc
        except Exception as exc:
            logger.error("Error invoking model %s: %s", self.model, str(exc))
            raise
