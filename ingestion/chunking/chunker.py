from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DocumentChunk:
    chunk_id: str
    document_id: str
    content: str
    chunk_index: int
    page_number: int | None = None
    section: str | None = None


class DocumentChunker:

    def __init__(
        self,
        chunk_size: int = 1200,
        chunk_overlap: int = 200,
    ) -> None:

        if chunk_overlap >= chunk_size:
            raise ValueError(
                "chunk_overlap must be smaller than chunk_size"
            )

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(
        self,
        document_id: str,
        text: str,
        page_number: int | None = None,
        section: str | None = None,
        starting_index: int = 0,
    ) -> list[DocumentChunk]:

        text = (text or "").strip()

        if not text:
            return []

        chunks: list[DocumentChunk] = []

        start = 0
        chunk_index = starting_index

        while start < len(text):

            end = min(
                start + self.chunk_size,
                len(text),
            )

            content = text[start:end].strip()

            if content:

                chunks.append(
                    DocumentChunk(
                        chunk_id=f"{document_id}-chunk-{chunk_index}",
                        document_id=document_id,
                        content=content,
                        chunk_index=chunk_index,
                        page_number=page_number,
                        section=section,
                    )
                )

                chunk_index += 1

            if end >= len(text):
                break

            start = end - self.chunk_overlap

        return chunks

    def chunk_blocks(
        self,
        document_id: str,
        blocks: list[dict],
    ) -> list[DocumentChunk]:

        chunks: list[DocumentChunk] = []

        for block in blocks:

            content = (block.get("content") or "").strip()

            if not content:
                continue

            block_chunks = self.chunk(
                document_id=document_id,
                text=content,
                page_number=block.get("page_number"),
                section=block.get("section"),
                starting_index=len(chunks),
            )

            chunks.extend(block_chunks)

        return chunks
