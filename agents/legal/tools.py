from __future__ import annotations

from typing import Any

from database.session import SessionLocal
from ingestion.embeddings.bge import BGEEmbeddingModel
from retrieval.repositories.document_repository import DocumentRepository


class LegalAgentTools:
    """
    Tools available to the Legal Due Diligence Agent.

    The LLM decides when to use these tools.
    The tools perform deterministic retrieval/database operations.
    """

    def __init__(self):
        self.embedder = BGEEmbeddingModel()

    def search_legal_documents(
        self,
        query: str,
        project_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Find documents in a project that are classified as legal.
        """

        session = SessionLocal()

        try:
            repository = DocumentRepository(session)

            query_embedding = self.embedder.embed_query(query)

            chunks = repository.search_similar_chunks(
                query_embedding=query_embedding,
                project_id=project_id,
                limit=limit,
            )

            results = []

            for chunk in chunks:
                document = chunk.document

                if document.category != "legal":
                    continue

                results.append(
                    {
                        "document_id": document.id,
                        "file_name": document.file_name,
                        "document_type": document.document_type,
                        "chunk_id": chunk.id,
                        "content": chunk.content,
                        "page_number": chunk.page_number,
                        "section": chunk.section,
                    }
                )

            return results

        finally:
            session.close()

    def search_contract_clause(
        self,
        clause_query: str,
        project_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Search legal documents for contract language relevant to a query.

        Examples:
            change of control
            termination
            assignment
            consent
            indemnification
        """

        return self.search_legal_documents(
            query=clause_query,
            project_id=project_id,
            limit=limit,
        )

    def search_legal_evidence(
        self,
        query: str,
        project_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Semantic evidence search across legal documents.
        """

        return self.search_legal_documents(
            query=query,
            project_id=project_id,
            limit=limit,
        )

    def read_document_page(
        self,
        document_id: str,
        page_number: int,
    ) -> dict[str, Any]:
        """
        Retrieve chunks associated with a specific document page.
        """

        session = SessionLocal()

        try:
            repository = DocumentRepository(session)

            document = repository.get_document(document_id)

            if document is None:
                return {
                    "found": False,
                    "error": f"Document not found: {document_id}",
                }

            chunks = repository.get_document_chunks(
                document_id
            )

            page_chunks = [
                chunk
                for chunk in chunks
                if chunk.page_number == page_number
            ]

            return {
                "found": True,
                "document_id": document.id,
                "file_name": document.file_name,
                "page_number": page_number,
                "chunks": [
                    {
                        "chunk_id": chunk.id,
                        "content": chunk.content,
                        "section": chunk.section,
                    }
                    for chunk in page_chunks
                ],
            }

        finally:
            session.close()

    def record_finding(
        self,
        finding: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Validate and return a structured finding.

        Persistent finding storage will be connected in the
        Evidence/Findings phase.
        """

        required_fields = [
            "title",
            "issue",
            "why_it_matters",
        ]

        missing = [
            field
            for field in required_fields
            if not finding.get(field)
        ]

        if missing:
            return {
                "recorded": False,
                "error": f"Missing required fields: {missing}",
            }

        return {
            "recorded": True,
            "finding": finding,
        }

    def request_evidence(
        self,
        description: str,
        project_id: str,
    ) -> dict[str, Any]:
        """
        Create a structured evidence request.

        Persistent request storage will be connected in the
        Requests/Tasks phase.
        """

        if not description.strip():
            return {
                "created": False,
                "error": "Evidence request description is required.",
            }

        return {
            "created": True,
            "project_id": project_id,
            "description": description,
            "status": "OPEN",
        }