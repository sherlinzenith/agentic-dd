from __future__ import annotations

from database.session import SessionLocal
from ingestion.embeddings.bge import BGEEmbeddingModel
from retrieval.repositories.document_repository import DocumentRepository


class DocumentSearchService:
    """
    Shared semantic document retrieval service.

    The service converts the agent's natural-language query into a
    BGE-M3 embedding and searches PostgreSQL + pgvector for the most
    relevant document chunks.

    The agent decides WHAT to search.
    This service decides HOW to retrieve matching evidence.
    """

    def __init__(
        self,
        embedder: BGEEmbeddingModel | None = None,
    ) -> None:
        self.embedder = embedder or BGEEmbeddingModel()

    def search(
        self,
        *,
        query: str,
        project_id: str,
        limit: int = 10,
        category: str | None = None,
    ) -> list[dict]:
        if not query.strip():
            return []

        session = SessionLocal()

        try:
            repository = DocumentRepository(session)

            query_embedding = self.embedder.embed_query(query)

            chunks = repository.search_similar_chunks(
                query_embedding=query_embedding,
                limit=limit,
                project_id=project_id,
            )

            results = []

            for chunk in chunks:
                document = chunk.document

                if category and document.category.lower() != category.lower():
                    continue

                results.append(
                    {
                        "document_id": document.id,
                        "document_name": document.file_name,
                        "category": document.category,
                        "document_type": document.document_type,
                        "chunk_id": chunk.id,
                        "chunk_index": chunk.chunk_index,
                        "page_number": chunk.page_number,
                        "section": chunk.section,
                        "content": chunk.content,
                    }
                )

            return results

        finally:
            session.close()
