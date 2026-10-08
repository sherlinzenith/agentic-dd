from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from retrieval.models.documents import Document, DocumentChunk


class DocumentRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_document(
        self,
        project_id: str,
        file_name: str,
        storage_key: str,
        category: str = "other",
        document_type: str | None = None,
    ) -> Document:
        document = Document(
            project_id=project_id,
            file_name=file_name,
            storage_key=storage_key,
            category=category,
            document_type=document_type,
        )

        self.session.add(document)
        self.session.flush()

        return document

    def create_chunk(
        self,
        document_id: str,
        chunk_index: int,
        content: str,
        embedding: list[float] | None = None,
        page_number: int | None = None,
        section: str | None = None,
    ) -> DocumentChunk:
        chunk = DocumentChunk(
            document_id=document_id,
            chunk_index=chunk_index,
            content=content,
            embedding=embedding,
            page_number=page_number,
            section=section,
        )

        self.session.add(chunk)
        self.session.flush()

        return chunk

    def get_document(self, document_id: str) -> Document | None:
        return self.session.get(Document, document_id)

    def get_document_chunks(
        self,
        document_id: str,
    ) -> Sequence[DocumentChunk]:
        statement = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        )

        return self.session.scalars(statement).all()

    def search_similar_chunks(
        self,
        query_embedding: list[float],
        limit: int = 10,
        project_id: str | None = None,
    ) -> Sequence[DocumentChunk]:
        distance = DocumentChunk.embedding.cosine_distance(
            query_embedding
        )

        statement = (
            select(DocumentChunk)
            .join(Document)
            .where(DocumentChunk.embedding.is_not(None))
            .order_by(distance)
            .limit(limit)
        )

        if project_id is not None:
            statement = statement.where(
                Document.project_id == project_id
            )

        return self.session.scalars(statement).all()

    def save(self) -> None:
        self.session.commit()
