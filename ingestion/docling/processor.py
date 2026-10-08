from __future__ import annotations

from pathlib import Path
from typing import Any

from docling.document_converter import DocumentConverter


class DoclingProcessor:
    """
    Converts supported business documents into structured content.

    Docling is responsible for document understanding/extraction.
    It does NOT classify the document and it does NOT perform DD reasoning.
    """

    def __init__(self) -> None:
        self.converter = DocumentConverter()

    def process(
        self,
        file_path: str | Path,
    ) -> dict[str, Any]:

        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Document not found: {path}"
            )

        result = self.converter.convert(
            str(path)
        )

        document = result.document

        markdown = document.export_to_markdown()

        return {
            "file_name": path.name,
            "file_path": str(path),
            "text": markdown,
            "source_format": path.suffix.lower(),
        }
