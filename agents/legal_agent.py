"""Legal DD workstream (subgraph used by the DD orchestrator).

identify -> (extract -> checks | END)

identify : find contract documents
extract  : risk clauses (with page + exact quote) and missing standard clauses
checks   : turn clauses into findings, one finding per clause per contract
"""

from typing import Dict, List, TypedDict

from langgraph.graph import END, START, StateGraph

from tools.legal_tools import (
    contract_title,
    extract_clauses,
    is_contract,
    missing_clauses,
)


class LegalDDState(TypedDict, total=False):
    documents: List[Dict]
    contracts: List[Dict]
    clauses: List[Dict]
    missing: List[Dict]
    findings: List[Dict]
    notes: List[str]
    status: str


def _next_id(findings):
    return f"LEG-{len(findings) + 1:03d}"


def _reasoning(issue, why, review, conclusion):
    return {
        "issue": issue,
        "why_it_matters": why,
        "what_should_be_reviewed": review,
        "evidence_conclusion": conclusion,
    }


# ---------------------------------------------------------------
# Node 1: identify contracts
# ---------------------------------------------------------------

def identify_node(state: LegalDDState):

    print("\n[Legal] Identifying contracts...")

    contracts = [d for d in state["documents"] if is_contract(d)]
    notes = [f"{d['document']}: {contract_title(d)}" for d in contracts]
    findings = list(state.get("findings", []))

    for name in notes:
        print(f"  contract: {name}")

    if not contracts:
        findings.append({
            "finding_id": _next_id(findings),
            "type": "MISSING_DOCUMENT",
            "category": "Missing Document",
            "severity": "MEDIUM",
            "status": "REVIEW_REQUIRED",
            "description": "No contract or agreement documents were found.",
            "impact": "Legal checks could not be performed.",
            "evidence": [],
            "ai_reasoning": _reasoning(
                "No contract or agreement documents were found.",
                "Legal checks depend on contract documents.",
                "Upload the contracts to the workspace.",
                "No contract was present in the supplied set.",
            ),
            "evidence_guard": {"status": "NOT_REQUIRED", "issues": []},
        })

    return {"contracts": contracts, "notes": notes, "findings": findings}


def route_after_identify(state: LegalDDState):
    return "extract" if state.get("contracts") else "end"


# ---------------------------------------------------------------
# Node 2: extract clauses
# ---------------------------------------------------------------

def extract_node(state: LegalDDState):

    print("\n[Legal] Extracting clauses...")

    clauses, missing = [], []

    for contract in state["contracts"]:
        clauses += extract_clauses(contract)
        missing += missing_clauses(contract)

    print(f"  risk clauses: {len(clauses)}   missing standard clauses: {len(missing)}")

    return {"clauses": clauses, "missing": missing}


# ---------------------------------------------------------------
# Node 3: findings
# ---------------------------------------------------------------

def checks_node(state: LegalDDState):

    findings = list(state.get("findings", []))

    # one finding per (contract, clause type), with every quote as evidence
    groups = {}
    for c in state.get("clauses", []):
        groups.setdefault((c["document"], c["clause_id"]), []).append(c)

    for (document, _), items in groups.items():

        first = items[0]
        pages = ", ".join(str(p) for p in sorted({i["page"] for i in items}))
        description = f"{first['label']} clause found in {document}."

        findings.append({
            "finding_id": _next_id(findings),
            "type": "CLAUSE",
            "category": first["label"],
            "severity": first["severity"],
            "status": "REVIEW_REQUIRED",
            "description": description,
            "impact": first["impact"],
            "evidence": [
                {
                    "document": i["document"],
                    "page": i["page"],
                    "field": i["label"],
                    "value": i["quote"],
                }
                for i in items
            ],
            "ai_reasoning": _reasoning(
                description,
                first["impact"],
                f"Review {document}, page {pages}, with legal counsel.",
                "The clause wording above was found verbatim in the document.",
            ),
            "evidence_guard": {"status": "PASSED", "issues": [], "method": "quote_verified"},
        })

    for m in state.get("missing", []):

        description = f"{m['label']} clause was not found in {m['document']}."

        findings.append({
            "finding_id": _next_id(findings),
            "type": "MISSING_CLAUSE",
            "category": "Missing Clause",
            "severity": "MEDIUM",
            "status": "REVIEW_REQUIRED",
            "description": description,
            "impact": f"The contract may not define {m['label'].lower()}.",
            "evidence": [],
            "ai_reasoning": _reasoning(
                description,
                f"A standard {m['label'].lower()} clause is normally expected.",
                f"Confirm with counsel whether {m['document']} should include it.",
                "No matching wording was found in any page of the document.",
            ),
            "evidence_guard": {"status": "NOT_REQUIRED", "issues": []},
        })

    print(f"\n[Legal] {len(findings)} finding(s)")

    return {"findings": findings}


# ---------------------------------------------------------------
# Graph
# ---------------------------------------------------------------

def build_legal_subgraph():

    graph = StateGraph(LegalDDState)

    graph.add_node("identify", identify_node)
    graph.add_node("extract", extract_node)
    graph.add_node("checks", checks_node)

    graph.add_edge(START, "identify")
    graph.add_conditional_edges(
        "identify", route_after_identify,
        {"extract": "extract", "end": END},
    )
    graph.add_edge("extract", "checks")
    graph.add_edge("checks", END)

    return graph.compile()