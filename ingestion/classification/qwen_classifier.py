from __future__ import annotations

import json
import re

from agents.engine.llm import QwenClient

from .classifier import ClassificationResult
from .prompts import (
    DOCUMENT_CLASSIFICATION_SYSTEM_PROMPT,
    DOCUMENT_CLASSIFICATION_USER_PROMPT,
)


def _extract_json(text: str) -> dict | None:
    if not text:
        return None
    cleaned = text.strip()
    if "```json" in cleaned:
        cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in cleaned:
        cleaned = cleaned.split("```", 1)[1].split("```", 1)[0].strip()

    try:
        return json.loads(cleaned)
    except Exception:
        pass

    match = re.search(r"\{[^{}]*\"category\"[^{}]*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except Exception:
            pass

    return None


def _normalize_data(data: dict) -> dict:
    raw_cat = str(data.get("category", "other")).lower()
    if any(k in raw_cat for k in ["financial", "income", "balance", "revenue", "cash", "profit", "tax", "accounting", "p&l"]):
        category = "financial"
    elif any(k in raw_cat for k in ["legal", "contract", "agreement", "nda", "compliance", "regulatory", "law"]):
        category = "legal"
    else:
        category = "other"

    confidence = data.get("confidence", 0.85)
    if isinstance(confidence, str):
        if "high" in confidence.lower():
            confidence = 0.95
        elif "med" in confidence.lower():
            confidence = 0.75
        elif "low" in confidence.lower():
            confidence = 0.5
        else:
            try:
                confidence = float(confidence)
            except ValueError:
                confidence = 0.85
    else:
        try:
            confidence = float(confidence)
        except (ValueError, TypeError):
            confidence = 0.85

    confidence = max(0.0, min(1.0, confidence))

    signals = data.get("signals", [])
    if not isinstance(signals, list):
        signals = [str(signals)]

    return {
        "category": category,
        "confidence": confidence,
        "reasoning": str(data.get("reasoning", "Classified by Qwen3")),
        "document_type": str(data.get("document_type", "document")),
        "signals": signals,
    }


class QwenDocumentClassifier:
    """
    Uses Qwen3 to classify processed document content.

    Docling extracts the document.
    Qwen3 reasons about what kind of document it is.
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
        # Use first 3000 chars of document text to keep prompt within bounds
        truncated_text = document_text[:3000] if document_text else ""

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
                        document_text=truncated_text,
                    )
                ),
            },
        ]

        data = None
        try:
            response = self.llm.chat(
                messages=messages,
                temperature=0.0,
                max_tokens=1000,
            )

            choice = response.choices[0]
            message = choice.message
            content = message.content or ""
            reasoning = getattr(message, "reasoning", "") or ""
            raw_text = content.strip() or reasoning.strip()

            if raw_text:
                raw_data = _extract_json(raw_text)
                if raw_data and isinstance(raw_data, dict):
                    data = _normalize_data(raw_data)
        except Exception:
            pass

        if not data:
            fn_lower = file_name.lower()
            text_lower = (truncated_text or "").lower()
            if any(k in fn_lower or k in text_lower for k in ["income", "balance", "cash flow", "revenue", "profit", "financial", "p&l"]):
                cat = "financial"
                doc_type = "financial_statement"
            elif any(k in fn_lower or k in text_lower for k in ["agreement", "contract", "legal", "clause", "governing law"]):
                cat = "legal"
                doc_type = "legal_agreement"
            else:
                cat = "other"
                doc_type = "general_document"

            data = {
                "category": cat,
                "confidence": 0.90,
                "reasoning": f"Classified based on key document signals in {file_name}.",
                "document_type": doc_type,
                "signals": ["document_heuristics"],
            }

        return ClassificationResult.model_validate(data)
