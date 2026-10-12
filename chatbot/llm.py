from __future__ import annotations

import logging
import os
from typing import Any, List, Optional
import urllib.request
import json

from dotenv import load_dotenv
from openai import APIConnectionError, APITimeoutError, NotFoundError, OpenAI

load_dotenv()
logger = logging.getLogger(__name__)


class LlamaChatbotClient:
    """
    Dedicated LLM client for the Evidence-Grounded Due Diligence Chatbot.
    Strictly isolated from analysis agents (Financial, Legal, Cross-Domain).
    Communicates with local Ollama using the configured Llama model.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        raw_url = base_url or os.getenv("LLAMA_BASE_URL", "http://localhost:11434/v1")
        if not raw_url.endswith("/v1"):
            raw_url = raw_url.rstrip("/") + "/v1"
        self.base_url = raw_url

        self.model = model or os.getenv("LLAMA_MODEL", "llama3.3:8b")
        self.api_key = os.getenv("LLAMA_API_KEY", "ollama")
        self.timeout = timeout or float(os.getenv("LLAMA_TIMEOUT", "120.0"))

        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=self.timeout,
        )

    def get_available_models(self) -> List[str]:
        """Queries local Ollama to list available installed models."""
        try:
            models_response = self.client.models.list()
            return [m.id for m in models_response.data]
        except Exception as exc:
            logger.warning("Could not list models from %s: %s", self.base_url, exc)
            return []

    def check_model_availability(self) -> dict[str, Any]:
        """
        Verifies if the configured model is installed in local Ollama.
        Returns a diagnostic status dict.
        """
        available = self.get_available_models()
        is_installed = self.model in available or any(self.model in m for m in available)
        return {
            "configured_model": self.model,
            "base_url": self.base_url,
            "is_installed": is_installed,
            "available_models": available,
        }

    def chat(
        self,
        messages: list[dict[str, Any]],
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> Any:
        """
        Sends chat completion request to the configured Llama model in Ollama.
        Catches model-not-found, connection, and timeout errors with clear diagnostics.
        """
        token_limit = max_tokens or int(os.getenv("LLAMA_MAX_TOKENS", "1500"))

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=token_limit,
            )
            if not response.choices:
                raise ValueError("Llama model returned an empty choices list.")
            return response
        except NotFoundError as exc:
            available = self.get_available_models()
            msg = (
                f"Configured Llama model '{self.model}' was not found in Ollama at '{self.base_url}'. "
                f"Available local models: {available}. "
                f"(Note: Meta released Llama 3.3 as 70B; the official 8B Llama model is 'llama3.1:latest')."
            )
            logger.error(msg)
            raise RuntimeError(msg) from exc
        except APITimeoutError as exc:
            msg = f"Timeout ({self.timeout}s) connecting to Llama model at {self.base_url}."
            logger.error(msg)
            raise TimeoutError(msg) from exc
        except APIConnectionError as exc:
            msg = f"Failed to connect to Llama service at {self.base_url}. Is Ollama running?"
            logger.error(msg)
            raise ConnectionError(msg) from exc
