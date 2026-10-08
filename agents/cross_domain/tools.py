from __future__ import annotations

from typing import Any

from database.session import SessionLocal
from retrieval.repositories.document_repository import DocumentRepository


class CrossDomainAgentTools:
    """
    Tools used by the Cross-Domain Agent.

    These tools retrieve and compare evidence from Financial and Legal
    investigations.
    """

    def search_cross_domain_evidence(
        self,
        query: str,
        project_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:

        session = SessionLocal()

        try:
            repository = DocumentRepository(session)

            from ingestion.embeddings.bge import BGEEmbeddingModel

            embedder = BGEEmbeddingModel()

            query_embedding = embedder.embed_query(query)

            chunks = repository.search_similar_chunks(
                query_embedding=query_embedding,
                project_id=project_id,
                limit=limit,
            )

            results = []

            for chunk in chunks:
                document = chunk.document

                if document.category not in {
                    "financial",
                    "legal",
                }:
                    continue

                results.append(
                    {
                        "document_id": document.id,
                        "file_name": document.file_name,
                        "category": document.category,
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

    def compare_findings(
        self,
        financial_findings: list[dict[str, Any]],
        legal_findings: list[dict[str, Any]],
    ) -> dict[str, Any]:

        return {
            "financial_findings": financial_findings,
            "legal_findings": legal_findings,
            "financial_count": len(financial_findings),
            "legal_count": len(legal_findings),
            "comparison_ready": True,
        }

    def inspect_evidence(
        self,
        evidence: list[dict[str, Any]],
    ) -> dict[str, Any]:

        return {
            "count": len(evidence),
            "evidence": evidence,
        }

    def record_cross_domain_finding(
        self,
        finding: dict[str, Any],
    ) -> dict[str, Any]:

        required = [
            "title",
            "issue",
            "why_it_matters",
        ]

        missing = [
            field
            for field in required
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

    def request_additional_evidence(
        self,
        description: str,
        project_id: str,
    ) -> dict[str, Any]:

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
