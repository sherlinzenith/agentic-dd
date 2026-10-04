"""Step 6 - Evidence verification (one shared gate for ALL workstreams).

For every evidence item: does the document exist, is the page real,
and does the quoted text / number actually appear on that page?
Findings are never deleted here - they are marked, and the reviewer sees the result.
"""

from tools.legal_tools import verify_quote
from workflow.activity import log


def _number_on_page(value, text):
    variants = {f"{value:.2f}", f"{value:,.2f}", f"{value:g}"}
    return any(v in text for v in variants)


def _check(evidence, docs):

    doc = docs.get(evidence.get("document"))

    if doc is None:
        return f"document '{evidence.get('document')}' not found"

    pages = doc.get("pages") or [doc.get("text", "")]
    page = evidence.get("page") or 1

    if not 1 <= page <= len(pages):
        return f"page {page} does not exist in {doc['document']}"

    value = evidence.get("value")

    if value is None:
        return None

    text = pages[page - 1]

    if isinstance(value, (int, float)):
        found = _number_on_page(float(value), text)
    else:
        found = verify_quote(str(value), text)

    return None if found else f"value not found on page {page} of {doc['document']}"


def verify_finding(finding, docs):

    evidence = finding.get("evidence") or []

    if not evidence:
        return {"status": "NO_EVIDENCE", "checked": 0, "verified": 0, "issues": []}

    issues = [i for i in (_check(e, docs) for e in evidence) if i]
    verified = len(evidence) - len(issues)

    status = "VERIFIED" if not issues else ("PARTIAL" if verified else "UNVERIFIED")

    return {"status": status, "checked": len(evidence), "verified": verified, "issues": issues}


def verify_node(state):

    docs = {d["document"]: d for d in state["documents"]}
    findings = []
    counts = {}

    for f in state.get("findings") or []:
        result = verify_finding(f, docs)
        counts[result["status"]] = counts.get(result["status"], 0) + 1
        findings.append({**f, "evidence_verification": result})

    print(f"\n[Evidence verification] {counts}")

    detail = ", ".join(f"{n} {s.lower().replace('_', ' ')}" for s, n in counts.items()) or "nothing to verify"

    return {"findings": findings, "activity": [log("evidence", detail)]}
