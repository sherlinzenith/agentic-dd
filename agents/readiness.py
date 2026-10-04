"""Step 2 - DD readiness: what should exist vs what was uploaded.

Informational only (it does not create findings). The Lead Agent and
the UI use it to show missing information up front.
"""

from workflow.activity import log

CHECKLISTS = {
    "financial": [
        ("Income statement", "income_statement"),
        ("Balance sheet", "balance_sheet"),
        ("Cash flow statement", "cash_flow"),
        ("Revenue report", "revenue_report"),
    ],
    "legal": [
        ("Contract / agreement", "contract"),
    ],
}


def readiness_node(state):

    scope = [s for s in (state.get("dd_types") or ["financial"]) if s in CHECKLISTS]
    inventory = state.get("inventory") or []

    readiness = {}

    for ws in scope:

        items = []

        for label, doc_type in CHECKLISTS[ws]:
            match = next((r["document"] for r in inventory if r["type"] == doc_type), None)
            items.append({"item": label, "present": match is not None, "document": match})

        present = sum(i["present"] for i in items)

        readiness[ws] = {
            "score": round(100 * present / len(items)),
            "items": items,
            "missing": [i["item"] for i in items if not i["present"]],
        }

    missing = sum(len(r["missing"]) for r in readiness.values())

    print(f"\n[Readiness] {missing} expected item(s) missing")

    return {
        "readiness": readiness,
        "activity": [log("readiness", f"{missing} expected document(s) missing")],
    }
