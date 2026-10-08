from __future__ import annotations

import json

from agents.engine.llm import QwenClient

from .classifier import ClassificationResult
from .prompts import (
    DOCUMENT_CLASSIFICATION_SYSTEM_PROMPT,
    DOCUMENT_CLASSIFICATION_USER_PROMPT,
)


class QwenDocumentClassifier:
    """
    Uses Qwen3 to classify processed document content.

    Docling extracts the document.
    Qwen3 reasons about what kind of document it is.

    There is intentionally no keyword-based classification here.
    """

    def __init__(
        self,
        llm: QwenClient | None = None,
    ) -> None:
        self.llm = llm or QwenClient()

    def classify(
        self,
        *,
        file_name: str,
        document_text: str,
    ) -> ClassificationResult:

        messages = [
            {
                "role": "system",
                "content": (
                    DOCUMENT_CLASSIFICATION_SYSTEM_PROMPT
                ),
            },
            {
                "role": "user",
                "content": (
                    DOCUMENT_CLASSIFICATION_USER_PROMPT.format(
                        file_name=file_name,
                        document_text=document_text,
                    )
                ),
            },
        ]

        response = self.llm.chat(
            messages=messages,
            temperature=0.0,
            max_tokens=1000,
        )

        content = (
            response.choices[0]
            .message
            .content
        )

        if not content:
            raise ValueError(
                "Qwen3 returned an empty classification response."
            )

        # Qwen3 is expected to return JSON.
        # We validate the result with Pydantic.
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "Qwen3 classification response was not valid JSON."
            ) from exc

        return ClassificationResult.model_validate(
            data
        )
