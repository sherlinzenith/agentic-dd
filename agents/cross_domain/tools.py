from __future__ import annotations

from typing import Any

from database.session import SessionLocal
from findings.repository import FindingRepository
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
            chunks = []

            try:
                from ingestion.embeddings.bge import BGEEmbeddingModel
                embedder = BGEEmbeddingModel()
                query_embedding = embedder.embed_query(query)
                chunks = repository.search_similar_chunks(
                    query_embedding=query_embedding,
                    project_id=project_id,
                    limit=limit,
                )
            except Exception:
                chunks = []

            # Reliable keyword search fallback if vector search produces 0 chunks
            if not chunks and query.strip():
                from sqlalchemy import select, or_
                from retrieval.models.documents import Document, DocumentChunk
                words = [w for w in query.split() if len(w) > 3]
                stmt = select(DocumentChunk).join(Document).where(Document.project_id == project_id)
                if words:
                    conds = [DocumentChunk.content.ilike(f"%{w}%") for w in words[:3]]
                    stmt = stmt.where(or_(*conds))
                stmt = stmt.limit(limit)
                chunks = session.scalars(stmt).all()

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
        """
        Compare Financial and Legal findings to detect potential cross-domain relationships,
        contradictions, and covenant risks.
        """
        correlations = []
        fin_text = " ".join(
            f"{f.get('title', '')} {f.get('issue', '')}".lower()
            for f in financial_findings
        )
        leg_text = " ".join(
            f"{f.get('title', '')} {f.get('issue', '')}".lower()
            for f in legal_findings
        )

        # Pattern 1: Revenue concentration vs customer termination / change of control
        if any(w in fin_text for w in ["revenue", "customer", "concentration", "sales"]) and any(w in leg_text for w in ["termination", "change of control", "assignment", "convenience"]):
            correlations.append({
                "type": "REVENUE_TERMINATION_RISK",
                "risk_severity": "high",
                "description": "High revenue concentration or customer dependence intersects with customer contract termination rights or change of control consent requirements.",
            })

        # Pattern 2: Debt, loans, or credit vs negative covenants or default clauses
        if any(w in fin_text for w in ["debt", "loan", "borrowing", "leverage", "ebitda", "interest"]) and any(w in leg_text for w in ["covenant", "default", "restriction", "pledge", "encumbrance"]):
            correlations.append({
                "type": "DEBT_COVENANT_RISK",
                "risk_severity": "high",
                "description": "Reported debt obligations, leverage, or interest coverage intersect with contractual negative covenants or acceleration triggers.",
            })

        # Pattern 3: Contingent liabilities / provisions vs legal claims / indemnities
        if any(w in fin_text for w in ["liability", "provision", "contingent", "tax", "reserve"]) and any(w in leg_text for w in ["litigation", "indemnity", "dispute", "claim", "penalty"]):
            correlations.append({
                "type": "LITIGATION_EXPOSURE_RISK",
                "risk_severity": "high",
                "description": "Active or threatened legal proceedings/indemnities create financial liability exposure not fully accounted for in financial provisions.",
            })

        return {
            "financial_findings": financial_findings,
            "legal_findings": legal_findings,
            "financial_count": len(financial_findings),
            "legal_count": len(legal_findings),
            "correlations": correlations,
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
        project_id: str | None = None,
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

        target_project_id = project_id or finding.get("project_id") or "REAL-INGESTION-TEST"
        session = SessionLocal()
        try:
            repo = FindingRepository(session)
            f_record = repo.create_finding({
                "project_id": target_project_id,
                "investigation_id": finding.get("investigation_id"),
                "workstream": "cross_domain",
                "agent_name": "cross_domain_dd_agent",
                "title": finding["title"],
                "issue": finding["issue"],
                "why_it_matters": finding["why_it_matters"],
                "evidence_conclusion": finding.get("conclusion") or finding.get("evidence_conclusion"),
                "recommended_action": finding.get("recommended_action"),
                "risk_severity": finding.get("risk_level", "high"),
                "confidence": str(finding.get("confidence", "high")),
                "status": "REVIEW_REQUIRED",
            })

            from retrieval.repositories.document_repository import DocumentRepository
            from services.evidence_validation_service import validate_single_evidence

            doc_repo = DocumentRepository(session)
            raw_docs = doc_repo.list_documents(target_project_id)
            project_docs = {d.file_name.lower(): d for d in raw_docs}
            doc_by_id = {d.id: d for d in raw_docs}

            evidence_items = list(finding.get("evidence", []) or [])

            # Also ground in supporting findings' evidence if referenced
            supporting_ids = finding.get("supporting_finding_ids") or []
            if isinstance(supporting_ids, list):
                for sf_id in supporting_ids:
                    sf = repo.get(sf_id)
                    if sf and sf.evidence:
                        for sf_ev in sf.evidence:
                            evidence_items.append({
                                "document_id": sf_ev.document_id,
                                "chunk_id": sf_ev.chunk_id,
                                "source_label": sf_ev.source_label,
                                "page_number": sf_ev.page_number,
                                "quoted_text": sf_ev.quoted_text,
                                "extracted_value": sf_ev.extracted_value,
                                "evidence_type": sf_ev.evidence_type,
                            })

            saved_evidence = []
            from retrieval.models.documents import Document, DocumentChunk
            for ev in (evidence_items or []):
                ev_doc_id = ev.get("document_id")
                if ev_doc_id and not session.get(Document, ev_doc_id):
                    ev_doc_id = None
                ev_chunk_id = ev.get("chunk_id")
                if ev_chunk_id and not session.get(DocumentChunk, ev_chunk_id):
                    ev_chunk_id = None

                ev_record = repo.add_evidence({
                    "project_id": target_project_id,
                    "finding_id": f_record.id,
                    "document_id": ev_doc_id,
                    "chunk_id": ev_chunk_id,
                    "evidence_type": ev.get("evidence_type", "document"),
                    "page_number": ev.get("page_number") or ev.get("page"),
                    "location": ev.get("location"),
                    "quoted_text": ev.get("quoted_text") or ev.get("content") or ev.get("text"),
                    "extracted_value": str(ev.get("extracted_value") or ev.get("value") or ""),
                    "source_label": ev.get("source_label") or ev.get("file_name"),
                    "validation_status": "UNVERIFIED",
                })

                val_res = validate_single_evidence(
                    ev=ev_record,
                    finding=f_record,
                    doc_repo=doc_repo,
                    project_docs=project_docs,
                    doc_by_id=doc_by_id,
                )
                ev_record.validation_status = val_res["status"]
                ev_record.validation_reason = val_res["reason"]
                ev_record.match_method = val_res["match_method"]
                ev_record.confidence = val_res["confidence"]
                if val_res["chunk_id"]:
                    ev_record.chunk_id = val_res["chunk_id"]
                if val_res["page_number"] and not ev_record.page_number:
                    ev_record.page_number = val_res["page_number"]
                if val_res["document_id"] and not ev_record.document_id:
                    ev_record.document_id = val_res["document_id"]

                saved_evidence.append(ev_record.id)

            repo.commit()

            return {
                "recorded": True,
                "status": "PERSISTED",
                "finding_id": f_record.id,
                "finding": finding,
                "evidence_count": len(saved_evidence),
            }
        except Exception as exc:
            repo.rollback()
            return {
                "recorded": False,
                "error": str(exc),
            }
        finally:
            session.close()

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
