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
    """
    Splits Docling-extracted document text into retrieval-friendly chunks.

    The chunker preserves document identity and ordering so every
    retrieved chunk can later be traced back to its source document.
    """

    def __init__(
        self,
        chunk_size: int = 1200,
        chunk_overlap: int = 200,
    ):
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(
        self,
        document_id: str,
        text: str,
    ) -> list[DocumentChunk]:

        text = text.strip()

        if not text:
            return []

        chunks: list[DocumentChunk] = []

        start = 0
        chunk_index = 0

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
                    )
                )

            if end >= len(text):
                break

            start = end - self.chunk_overlap
            chunk_index += 1

        return chunks
