from __future__ import annotations

from pathlib import Path
from typing import Any

from docling.document_converter import DocumentConverter


class DoclingProcessor:
    """
    Converts business documents into structured retrieval content.

    Preserves:
    - page number
    - section/header context
    - text
    - tables as markdown

    Docling performs document understanding.
    Qwen performs classification/reasoning.
    """

    def __init__(self) -> None:
        self.converter = DocumentConverter()

    def process(self, file_path: str | Path) -> dict[str, Any]:
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Document not found: {path}")

        result = self.converter.convert(str(path))
        document = result.document

        blocks: list[dict[str, Any]] = []
        tables: list[dict[str, Any]] = []

        current_section: str | None = None

        for item, level in document.iterate_items():

            page_number: int | None = None

            provenance = getattr(item, "prov", None)

            if provenance:
                try:
                    page_number = provenance[0].page_no
                except Exception:
                    page_number = None

            item_type = type(item).__name__

            if item_type == "TableItem":

                try:
                    content = item.export_to_markdown(doc=document)
                except Exception:
                    content = ""

                content = (content or "").strip()

                if content:

                    table_index = len(tables)

                    tables.append(
                        {
                            "table_index": table_index,
                            "page_number": page_number,
                            "section": current_section,
                            "content": content,
                        }
                    )

                    blocks.append(
                        {
                            "content": content,
                            "page_number": page_number,
                            "section": current_section,
                            "content_type": "table",
                            "table_index": table_index,
                        }
                    )

                continue

            text = getattr(item, "text", None)

            if not text:
                text = getattr(item, "orig", None)

            text = (text or "").strip()

            if not text:
                continue

            label = str(getattr(item, "label", "")).lower()

            if "section_header" in label or "title" in label:
                current_section = text

            blocks.append(
                {
                    "content": text,
                    "page_number": page_number,
                    "section": current_section,
                    "content_type": "text",
                    "table_index": None,
                }
            )

        markdown = document.export_to_markdown()

        return {
            "file_name": path.name,
            "file_path": str(path),
            "text": markdown,
            "blocks": blocks,
            "tables": tables,
            "page_count": (
                document.num_pages()
                if callable(getattr(document, "num_pages", None))
                else (
                    getattr(document, "num_pages", None)
                    if getattr(document, "num_pages", None) is not None
                    else len(document.pages)
                )
            ),
            "table_count": len(tables),
            "source_format": path.suffix.lower(),
        }
