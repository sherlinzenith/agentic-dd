"""Single model access layer.

Development uses Ollama over HTTP. Production can replace this provider
without changing agent code.
"""
from typing import Any, Optional
from .config import config


def _ollama_client():
    try:
        from ollama import Client
    except ImportError as exc:
        raise RuntimeError("Install the ollama package to use the local model gateway.") from exc
    return Client(host=config.base_url, timeout=config.timeout_seconds)


def generate_agent(prompt: str, *, system: Optional[str] = None, format: Optional[Any] = None) -> str:
    client = _ollama_client()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    kwargs = {"model": config.agent_model, "messages": messages}
    if format is not None:
        kwargs["format"] = format
    response = client.chat(**kwargs)
    return response["message"]["content"]


def generate_chat(prompt: str, *, system: Optional[str] = None) -> str:
    client = _ollama_client()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    response = client.chat(model=config.chat_model, messages=messages)
    return response["message"]["content"]


def get_agent_model() -> str:
    return config.agent_model


def get_chat_model() -> str:
    return config.chat_model
