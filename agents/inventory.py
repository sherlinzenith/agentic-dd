"""Step 1 - Document inventory (document intelligence).

Every workspace document gets a category (financial / legal / other),
a type and a page count BEFORE any agent reasons about it.
A reviewer can override the category (state["overrides"]).
"""

from processing import document_classifier as _dc
from tools.legal_tools import is_contract
from workflow.activity import log

FINANCIAL_TYPES = {"income_statement", "balance_sheet", "cash_flow", "revenue_report"}
CATEGORIES = ("financial", "legal", "other")


def _classify(doc):
    if hasattr(_dc, "classify_document"):
        return _dc.classify_document(doc)
    return _dc.classify_documents([doc])[0]


def organize(documents, overrides=None):
    """Return one inventory row per document (pure function, reused by the UI)."""

    overrides = overrides or {}
    rows = []

    for doc in documents:

        c = _classify(doc)
        pages = len(doc.get("pages") or [doc.get("text", "")])
        reason = c.get("reason", "")

        if c.get("type") in FINANCIAL_TYPES:
            category, doc_type, confidence = "financial", c["type"], c.get("confidence", 0.0)
        elif is_contract(doc):
            category, doc_type, confidence = "legal", "contract", 0.9
            reason = "contract wording found in the document"
        else:
            category, doc_type, confidence = "other", "unclassified", 0.0
            reason = reason or "not enough matching content"

        manual = False
        forced = overrides.get(doc["document"])

        if forced in CATEGORIES and forced != category:
            manual = True
            category = forced
            doc_type = "contract" if forced == "legal" else ("unclassified" if forced == "other" else doc_type)
            confidence = 1.0
            reason = "category set by a reviewer"

        rows.append({
            "document": doc["document"],
            "pages": pages,
            "category": category,
            "type": doc_type,
            "confidence": confidence,
            "reason": reason,
            "manual": manual,
        })

    return rows


def summarize(rows):
    return {
        "total": len(rows),
        "financial": sum(r["category"] == "financial" for r in rows),
        "legal": sum(r["category"] == "legal" for r in rows),
        "other": sum(r["category"] == "other" for r in rows),
    }


def inventory_node(state):

    rows = organize(state["documents"], state.get("overrides"))
    summary = summarize(rows)

    print(f"\n[Inventory] {summary}")

    return {
        "inventory": rows,
        "inventory_summary": summary,
        "activity": [log(
            "inventory",
            f"{summary['total']} documents organized: {summary['financial']} financial, "
            f"{summary['legal']} legal, {summary['other']} other",
        )],
    }
