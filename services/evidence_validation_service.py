from __future__ import annotations

import difflib
import logging
import re
from typing import Any

from database.session import SessionLocal
from evidence.models import Evidence
from findings.models import Finding
from findings.repository import FindingRepository
from retrieval.models.documents import Document, DocumentChunk
from retrieval.repositories.document_repository import DocumentRepository
from tools.evidence_guard import (
    contains_unsupported_claim,
    extract_financial_numbers,
    normalize_text,
)

logger = logging.getLogger(__name__)


def normalize_quotation(text: str | None) -> str:
    """
    Safely normalize text for exact and fuzzy matching without changing meaning.
    - Normalizes smart quotes and backticks to standard ASCII quotes.
    - Normalizes en-dash, em-dash, and minus signs to standard hyphens.
    - Normalizes non-breaking spaces and redundant whitespaces.
    - Strips currency spacing (e.g. '₹ 100' -> '₹100').
    - Case-folds to lowercase.
    """
    if not text:
        return ""

    s = str(text)

    # 1. Unicode quotes and backticks
    s = s.replace("“", '"').replace("”", '"')
    s = s.replace("‘", "'").replace("’", "'")
    s = s.replace("`", "'")

    # 2. Unicode dashes and minuses
    s = s.replace("–", "-").replace("—", "-").replace("−", "-")

    # 3. Non-breaking spaces and zero-width spaces
    s = s.replace("\u00a0", " ").replace("\u200b", "").replace("\ufeff", "")

    # 4. Currency and number spacing (e.g., '₹ 100' or '$ 50')
    s = re.sub(r"([₹$€£])\s+(\d)", r"\1\2", s)

    # 5. Collapse all whitespace into a single space and strip
    s = re.sub(r"\s+", " ", s).strip()

    return s.lower()


def _best_window_similarity(query: str, text: str) -> float:
    """
    Find the highest similarity of query against candidate windows in text.
    Handles matching a shorter quotation against a long document chunk.
    """
    if not query or not text:
        return 0.0

    if query in text:
        return 1.0

    query_len = len(query)
    text_len = len(text)

    if text_len <= query_len * 1.5:
        return difflib.SequenceMatcher(None, query, text).ratio()

    # Step through candidate windows of approximate query length
    step = max(1, query_len // 4)
    best_ratio = 0.0
    window_sizes = [int(query_len * 0.9), query_len, int(query_len * 1.1)]

    for w_size in window_sizes:
        for i in range(0, text_len - w_size + 1, step):
            sub = text[i : i + w_size]
            ratio = difflib.SequenceMatcher(None, query, sub).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                if best_ratio >= 0.98:
                    return best_ratio

    return best_ratio


def validate_single_evidence(
    ev: Evidence,
    finding: Finding,
    doc_repo: DocumentRepository,
    project_docs: dict[str, Document],
    doc_by_id: dict[str, Document],
) -> dict[str, Any]:
    """
    Validate a single evidence record against stored document chunks.

    Returns a dict with:
      - status: VERIFIED | UNVERIFIED | FLAGGED_DISCREPANCY | AMBIGUOUS | UNSUPPORTED_CLAIM
      - reason: Explanation of the verification decision
      - match_method: exact | fuzzy_ngram | numeric_check | none
      - confidence: float between 0.0 and 1.0
      - chunk_id: resolved chunk id (if any)
      - page_number: resolved page number (if any)
      - document_id: resolved document id (if any)
    """
    result: dict[str, Any] = {
        "status": "UNVERIFIED",
        "reason": "",
        "match_method": "none",
        "confidence": 0.0,
        "chunk_id": ev.chunk_id,
        "page_number": ev.page_number,
        "document_id": ev.document_id,
    }

    # Check 1: Empty or missing quotation
    raw_quote = (ev.quoted_text or "").strip()
    if not raw_quote:
        result["status"] = "UNVERIFIED"
        result["reason"] = "Empty or missing quotation text in evidence record."
        return result

    # Check 2: Unsupported claims / speculative terms
    unsupported = contains_unsupported_claim(raw_quote)
    if unsupported:
        result["status"] = "UNSUPPORTED_CLAIM"
        result["reason"] = f"Quotation contains unsupported speculative claims: {', '.join(unsupported)}."
        result["confidence"] = 0.0
        return result

    # Check 3: Document Resolution
    doc: Document | None = None
    if ev.document_id and ev.document_id in doc_by_id:
        doc = doc_by_id[ev.document_id]
    elif ev.source_label:
        clean_label = ev.source_label.strip().lower()
        for fn, d in project_docs.items():
            if fn in clean_label or clean_label in fn:
                doc = d
                result["document_id"] = d.id
                break

    if not doc:
        result["status"] = "UNVERIFIED"
        result["reason"] = f"Referenced document '{ev.source_label or 'unknown'}' not found in project library."
        return result

    result["document_id"] = doc.id

    # Check 4: Exact vs Conservative Fuzzy Match against Chunks
    norm_quote = normalize_quotation(raw_quote)
    chunks = doc_repo.get_document_chunks(doc.id)

    if not chunks:
        result["status"] = "UNVERIFIED"
        result["reason"] = f"No text chunks found for document '{doc.file_name}'. Document may need re-ingestion."
        return result

    exact_matches: list[DocumentChunk] = []
    fuzzy_matches: list[tuple[float, DocumentChunk]] = []

    for chunk in chunks:
        norm_chunk = normalize_quotation(chunk.content)
        if norm_quote in norm_chunk:
            exact_matches.append(chunk)
        else:
            # Conservative fuzzy matching only for quotes >= 15 characters (avoiding short false positives)
            if len(norm_quote) >= 15:
                sim = _best_window_similarity(norm_quote, norm_chunk)
                if sim >= 0.70:
                    fuzzy_matches.append((sim, chunk))

    # Evaluate quotation matches
    matched_chunk: DocumentChunk | None = None

    if exact_matches:
        # Exact match confirmed
        matched_chunk = exact_matches[0]
        result["match_method"] = "exact"
        result["confidence"] = 1.0
        result["chunk_id"] = matched_chunk.id
        result["page_number"] = matched_chunk.page_number or ev.page_number
        result["status"] = "VERIFIED"
        result["reason"] = (
            f"Exact quotation verified in '{doc.file_name}' "
            f"(page {result['page_number'] or 1}, chunk {matched_chunk.id})."
        )
    elif fuzzy_matches:
        # Sort by similarity descending
        fuzzy_matches.sort(key=lambda x: x[0], reverse=True)
        best_score, best_chunk = fuzzy_matches[0]

        # Conservative threshold: >= 0.85
        if best_score >= 0.85:
            # Check for ambiguity: multiple competing chunks close to the top score
            competing = [c for s, c in fuzzy_matches if s >= 0.80 and c.id != best_chunk.id]
            if competing:
                result["status"] = "AMBIGUOUS"
                result["confidence"] = round(best_score, 2)
                result["reason"] = (
                    f"Ambiguous match: multiple chunks match with moderate confidence ({best_score:.2f}) "
                    f"in '{doc.file_name}' without unique exact text."
                )
                return result
            else:
                matched_chunk = best_chunk
                result["match_method"] = "fuzzy_ngram"
                result["confidence"] = round(best_score, 2)
                result["chunk_id"] = matched_chunk.id
                result["page_number"] = matched_chunk.page_number or ev.page_number
                result["status"] = "VERIFIED"
                result["reason"] = (
                    f"Conservative fuzzy match ({best_score:.2f} confidence) confirmed in '{doc.file_name}' "
                    f"(page {result['page_number'] or 1}, chunk {matched_chunk.id})."
                )
        elif best_score >= 0.70:
            result["status"] = "AMBIGUOUS"
            result["confidence"] = round(best_score, 2)
            result["reason"] = (
                f"Quotation match confidence ({best_score:.2f}) is below strict verification threshold (0.85) "
                f"in '{doc.file_name}'."
            )
            return result
        else:
            result["status"] = "UNVERIFIED"
            result["reason"] = f"Quoted text not found in source document '{doc.file_name}'."
            return result
    else:
        result["status"] = "UNVERIFIED"
        result["reason"] = f"Quoted text not found in any chunks of '{doc.file_name}'."
        return result

    # Check 5: Numeric Claims & Arithmetic Consistency
    # If an extracted numeric value was cited, verify it appears in the matched chunk
    if ev.extracted_value and matched_chunk:
        extracted_nums = extract_financial_numbers(str(ev.extracted_value))
        chunk_nums = extract_financial_numbers(matched_chunk.content)
        chunk_nums_set = {round(n, 4) for n in chunk_nums}

        for num in extracted_nums:
            if round(num, 4) not in chunk_nums_set:
                result["status"] = "UNVERIFIED"
                result["reason"] = (
                    f"Cited numeric value {num} does not occur in matched chunk "
                    f"(chunk {matched_chunk.id}, page {matched_chunk.page_number})."
                )
                return result

    # Check 6: Check Arithmetic Discrepancies if finding describes a mismatch/discrepancy
    finding_text = f"{finding.title} {finding.issue} {finding.evidence_conclusion or ''}".lower()
    if any(k in finding_text for k in ["discrepancy", "difference", "mismatch", "unreconciled", "variance"]):
        # Extract numbers to check if the discrepancy claim has true arithmetic backing
        all_finding_numbers = extract_financial_numbers(finding_text)
        if len(all_finding_numbers) >= 2:
            val1, val2 = all_finding_numbers[0], all_finding_numbers[1]
            diff = abs(val1 - val2)
            if diff > 0.001:
                # Discrepancy is genuinely demonstrated by cited numbers
                result["status"] = "FLAGGED_DISCREPANCY"
                result["reason"] = (
                    f"{result['reason']} Genuine arithmetic discrepancy confirmed: "
                    f"|{val1} - {val2}| = {diff:.2f}."
                )
            else:
                result["status"] = "UNVERIFIED"
                result["reason"] = f"Claimed discrepancy between {val1} and {val2} resolves to 0.00 difference."

    return result


def validate_project_evidence_service(project_id: str, session) -> dict[str, Any]:
    """
    Central Evidence Validation and Source Tracking Service.
    Validates all evidence records for a project with strict source-grounding,
    deterministic normalization, conservative n-gram fuzzy matching, and numeric checks.
    """
    finding_repo = FindingRepository(session)
    doc_repo = DocumentRepository(session)

    findings = finding_repo.list_for_project(project_id)
    raw_docs = doc_repo.list_documents(project_id)
    project_docs = {doc.file_name.lower(): doc for doc in raw_docs}
    doc_by_id = {doc.id: doc for doc in raw_docs}

    total_evidence = 0
    verified_count = 0
    unverified_count = 0
    discrepancy_count = 0
    ambiguous_count = 0
    unsupported_count = 0
    details = []

    for finding in findings:
        for ev in (finding.evidence or []):
            total_evidence += 1

            val_res = validate_single_evidence(
                ev=ev,
                finding=finding,
                doc_repo=doc_repo,
                project_docs=project_docs,
                doc_by_id=doc_by_id,
            )

            # Update evidence record in DB
            ev.validation_status = val_res["status"]
            ev.validation_reason = val_res["reason"]
            ev.match_method = val_res["match_method"]
            ev.confidence = val_res["confidence"]

            if val_res["chunk_id"]:
                ev.chunk_id = val_res["chunk_id"]
            if val_res["page_number"] and not ev.page_number:
                ev.page_number = val_res["page_number"]
            if val_res["document_id"] and not ev.document_id:
                ev.document_id = val_res["document_id"]

            # Count statuses
            status = val_res["status"]
            if status == "VERIFIED":
                verified_count += 1
            elif status == "FLAGGED_DISCREPANCY":
                discrepancy_count += 1
            elif status == "AMBIGUOUS":
                ambiguous_count += 1
            elif status == "UNSUPPORTED_CLAIM":
                unsupported_count += 1
            else:
                unverified_count += 1

            doc_name = doc_by_id.get(ev.document_id).file_name if ev.document_id and ev.document_id in doc_by_id else ev.source_label
            details.append({
                "evidence_id": ev.id,
                "finding_id": finding.id,
                "workstream": finding.workstream,
                "document": doc_name,
                "chunk_id": ev.chunk_id,
                "page": ev.page_number,
                "status": status,
                "match_method": val_res["match_method"],
                "confidence": val_res["confidence"],
                "reason": val_res["reason"],
            })

    session.commit()

    return {
        "total_evidence": total_evidence,
        "verified_count": verified_count,
        "unverified_count": unverified_count,
        "discrepancy_count": discrepancy_count,
        "ambiguous_count": ambiguous_count,
        "unsupported_count": unsupported_count,
        "details": details,
    }
