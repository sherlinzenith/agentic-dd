"""Central model configuration.

Models are configured through environment variables so agents never hardcode
provider/model details.
"""
from dataclasses import dataclass
import os

@dataclass(frozen=True)
class ModelConfig:
    provider: str = os.getenv("LLM_PROVIDER", "ollama")
    base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    agent_model: str = os.getenv("AGENT_MODEL", "qwen3:14b")
    chat_model: str = os.getenv("CHAT_MODEL", "llama3.3:8b")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
    timeout_seconds: int = int(os.getenv("LLM_TIMEOUT_SECONDS", "180"))

config = ModelConfig()
