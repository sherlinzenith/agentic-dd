"""Financial DD agent as a LangGraph workflow (one node per step).

START -> classify -> completeness -> (extract | save)
extract -> checks -> (reason | save) -> save -> END
"""

from pathlib import Path
from typing import Dict, List, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from agents.lead_agent import lead_node, route_after_lead

from findings.finding_store import (
    load_findings,
    load_metrics,
    reopen_more_evidence,
    save_findings,
    save_metrics,
)
from processing.document_classifier import classify_documents
from processing.document_processor import extract_all_documents
from tools.document_tools import (
    extract_balance_details,
    extract_cash_flow_details,
    extract_revenue_note,
    extract_balance_sheet,
    extract_cash_flow,
    extract_income_statement,
    extract_revenue_report,
)
from tools.evidence_guard import create_safe_reasoning, validate_reasoning
from tools.financial_tools import (
    compute_metrics,
    reconciliation_checks,
    check_balance_sheet,
    check_cash_flow,
    check_income_statement,
    check_revenue_consistency,
)


# ---------------------------------------------------------------
# State
# ---------------------------------------------------------------

class FinancialDDState(TypedDict, total=False):
    documents: List[Dict]      # raw documents (name + text)
    doc_types: List[Dict]      # classifier output per document
    selected: Dict[str, Dict]  # doc type -> chosen document
    notes: List[str]           # duplicates / unclassified files
    extracted: Dict[str, Dict]
    findings: List[Dict]
    metrics: List[Dict]
    status: str
    dd_types: List[str]
    plan: List[str]
    lead_notes: List[str]


DOCUMENTS_DIR = Path(__file__).resolve().parent.parent / "documents"

REQUIRED_TYPES = {
    "income_statement": "Income Statement",
    "balance_sheet": "Balance Sheet",
    "cash_flow": "Cash Flow Statement",
    "revenue_report": "Quarterly Revenue Report",
}


def _complete(data):
    return bool(data) and all(v is not None for v in data.values())


def _next_id(findings):
    return f"FIN-{len(findings) + 1:03d}"


def _file(state, doc_type):
    return state["selected"][doc_type]["document"]


# ---------------------------------------------------------------
# Model access (loaded only when reasoning is needed)
# ---------------------------------------------------------------

def _ask_model(prompt):
    """Returns (reasoning_dict | None, error | None) from the model gateway."""
    from models.gateway import ask_reasoning

    return ask_reasoning(prompt)


# ---------------------------------------------------------------
# Node 1: classify documents by content
# ---------------------------------------------------------------

def classify_node(state: FinancialDDState):

    print("\n[Classify] Detecting document types...")

    doc_types = classify_documents(state["documents"])
    by_name = {d["document"]: d for d in state["documents"]}

    selected, notes = {}, []

    for item in sorted(doc_types, key=lambda x: -x["confidence"]):

        t = item["type"]

        if t == "unclassified":
            notes.append(f"{item['document']}: could not be classified")
            continue

        if t in selected:
            notes.append(
                f"{item['document']}: duplicate {t}; "
                f"using {selected[t]['document']}"
            )
            continue

        selected[t] = by_name[item["document"]]

    for item in doc_types:
        print(f"  {item['document']} -> {item['type']} ({item['confidence']})")

    return {"doc_types": doc_types, "selected": selected, "notes": notes}


# ---------------------------------------------------------------
# Node 2: completeness (missing documents)
# ---------------------------------------------------------------

def completeness_node(state: FinancialDDState):

    findings = list(state.get("findings", []))

    for doc_type, label in REQUIRED_TYPES.items():

        if doc_type not in state["selected"]:

            findings.append({
                "finding_id": _next_id(findings),
                "type": "MISSING_DOCUMENT",
                "category": "Missing Document",
                "severity": "MEDIUM",
                "status": "REVIEW_REQUIRED",
                "description": f"Required document '{label}' was not found.",
                "impact": "Related checks could not be performed.",
                "evidence": [],
            })

    return {"findings": findings}


def route_after_completeness(state: FinancialDDState):

    return "extract" if state["selected"] else "save"


# ---------------------------------------------------------------
# Node 3: deterministic extraction
# ---------------------------------------------------------------

def _text(state, doc_type):
    doc = state["selected"].get(doc_type)
    return doc["text"] if doc else ""


def extract_node(state: FinancialDDState):

    print("\n[Extract] Reading financial values...")

    extracted = {
        "income": extract_income_statement(_text(state, "income_statement")),
        "balance": extract_balance_sheet(_text(state, "balance_sheet")),
        "cashflow": extract_cash_flow(_text(state, "cash_flow")),
        "revenue": extract_revenue_report(_text(state, "revenue_report")),
        "balance_detail": extract_balance_details(_text(state, "balance_sheet")),
        "cash_detail": extract_cash_flow_details(_text(state, "cash_flow")),
        "rev_note": extract_revenue_note(_text(state, "revenue_report")),
    }

    for name in ("income", "balance", "cashflow", "revenue"):
        print(f"  {name}: {extracted[name]}")

    return {"extracted": extracted}


# ---------------------------------------------------------------
# Node 4: financial checks
# ---------------------------------------------------------------

def checks_node(state: FinancialDDState):

    print("\n[Checks] Running financial checks...")

    findings = list(state.get("findings", []))
    x = state["extracted"]
    income, balance, cashflow, revenue = (
        x["income"], x["balance"], x["cashflow"], x["revenue"]
    )

    def calc_finding(category, check, doc_type, message):
        return {
            "finding_id": _next_id(findings),
            "category": category,
            "severity": "MEDIUM",
            "status": "REVIEW_REQUIRED",
            "description": message,
            "impact": (
                f"Reported {check['actual']:.2f} vs "
                f"calculated {check['expected']:.2f}."
            ),
            "evidence": [
                {
                    "document": _file(state, doc_type),
                    "page": 1,
                    "field": f"{check['check']} (reported)",
                    "value": check["actual"],
                },
                {
                    "document": _file(state, doc_type),
                    "page": 1,
                    "field": f"{check['check']} (calculated)",
                    "value": check["expected"],
                },
            ],
        }

    # Income statement
    if _complete(income):

        for check in check_income_statement(
            revenue=income["Revenue"],
            cogs=income["COGS"],
            gross_profit=income["Gross Profit"],
            operating_expenses=income["Operating Expenses"],
            operating_profit=income["Operating Profit"],
            finance_cost=income["Finance Cost"],
            pbt=income["PBT"],
            tax=income["Tax"],
            pat=income["PAT"],
        ):
            if check["status"] != "PASS":
                findings.append(calc_finding(
                    "Income Statement", check, "income_statement",
                    f"{check['check']} does not match.",
                ))

    # Balance sheet
    if _complete(balance):

        check = check_balance_sheet(
            balance["Total Assets"],
            balance["Total Liabilities and Equity"],
        )
        if check["status"] != "PASS":
            findings.append(calc_finding(
                "Balance Sheet", check, "balance_sheet",
                "Total Assets does not match Total Liabilities and Equity.",
            ))

    # Cash flow
    if _complete(cashflow):

        check = check_cash_flow(
            cashflow["Opening Cash"],
            cashflow["Net Change"],
            cashflow["Closing Cash"],
        )
        if check["status"] != "PASS":
            findings.append(calc_finding(
                "Cash Flow", check, "cash_flow",
                "Closing Cash does not match Opening Cash + Net Change.",
            ))

    # Revenue across documents
    if _complete(income) and _complete(revenue):

        check = check_revenue_consistency(
            income["Revenue"],
            revenue["Total Revenue"],
        )
        if check["status"] != "PASS":
            findings.append({
                "finding_id": _next_id(findings),
                "category": "Revenue",
                "severity": "HIGH",
                "status": "REVIEW_REQUIRED",
                "description": (
                    "Revenue reported in the Income Statement "
                    "does not match the Total Revenue reported "
                    "in the Quarterly Revenue Report."
                ),
                "impact": f"Revenue differs by \u20b9{check['difference']:.2f} Cr.",
                "evidence": [
                    {
                        "document": _file(state, "income_statement"),
                        "page": 1,
                        "field": "Revenue",
                        "value": income["Revenue"],
                    },
                    {
                        "document": _file(state, "revenue_report"),
                        "page": 1,
                        "field": "Total Revenue",
                        "value": revenue["Total Revenue"],
                    },
                ],
            })

    # Extra arithmetic and cross-document reconciliation checks
    for spec in reconciliation_checks(x):

        findings.append({
            "finding_id": _next_id(findings),
            "category": spec["category"],
            "severity": spec["status"],
            "status": "REVIEW_REQUIRED",
            "description": spec["description"],
            "impact": f"Values differ by \u20b9{spec['difference']:.2f} Cr.",
            "evidence": [
                {
                    "document": _file(state, spec[side]["doc"]),
                    "page": 1,
                    "field": spec[side]["field"],
                    "value": spec[side]["value"],
                }
                for side in ("a", "b")
            ],
        })

    metrics = compute_metrics(x)

    print(f"  findings so far: {len(findings)}")
    print(f"  metrics computed: {len(metrics)}")

    return {"findings": findings, "metrics": metrics}


def route_after_checks(state: FinancialDDState):

    return "reason" if state.get("findings") else "save"


# ---------------------------------------------------------------
# Node 5: AI reasoning + Evidence Guard
# ---------------------------------------------------------------

PROMPT = """
Financial Due Diligence Finding

Finding ID:
{fid}

Category:
{category}

Severity:
{severity}

Verified Finding:
{description}

Verified Impact:
{impact}

Verified Evidence:
{evidence_text}

Exact Source Documents:
{source_documents}

Return ONLY valid JSON using exactly this structure:

{{
  "issue": "State only what the supplied evidence shows.",
  "why_it_matters": "Explain only that the documented discrepancy should be reviewed or reconciled.",
  "what_should_be_reviewed": "Name EVERY supplied source document using its exact filename.",
  "evidence_conclusion": "State only what the supplied evidence proves."
}}

STRICT RULES:

1. Use ONLY the verified finding and verified evidence.
2. Do not introduce a possible cause.
3. Do not speculate about why the discrepancy occurred.
4. Do not mention fraud.
5. Do not mention fraudulent activity.
6. Do not mention manipulation.
7. Do not mention misreporting.
8. Do not claim an accounting error.
9. Do not claim incorrect data.
10. Do not mention revenue recognition.
11. Do not mention inventory management.
12. Do not mention financial processes.
13. Do not mention internal controls unless explicitly present in the evidence.
14. Do not say "actual revenue".
15. Do not say "true revenue".
16. Do not say "ensure accuracy".
17. Do not introduce numbers that are not in the evidence.
18. Do not introduce documents that are not in the evidence.
19. If the evidence only proves a discrepancy, state only that discrepancy.
20. Do not make a conclusion about the cause of the discrepancy.
21. In "what_should_be_reviewed", include EVERY exact filename from the "Exact Source Documents" section.
22. Do not shorten, rename, or paraphrase the source filenames.
"""


def reason_node(state: FinancialDDState):

    print("\n[Reason] AI reasoning + Evidence Guard...")

    findings = list(state["findings"])

    for finding in findings:

        if finding.get("type") == "MISSING_DOCUMENT":

            finding["ai_reasoning"] = {
                "issue": finding["description"],
                "why_it_matters": (
                    "Checks that depend on this document could not be run."
                ),
                "what_should_be_reviewed": (
                    "Upload the missing document to the workspace."
                ),
                "evidence_conclusion": (
                    "The document was not present in the supplied set."
                ),
            }
            finding["evidence_guard"] = {"status": "NOT_REQUIRED", "issues": []}
            continue

        evidence_text = "\n".join(
            f"Document: {e['document']} | Page: {e.get('page', 'N/A')} | "
            f"Field: {e['field']} | Value: {e['value']}"
            for e in finding["evidence"]
        )

        source_documents = ", ".join(
            sorted({e["document"] for e in finding["evidence"]})
        )

        prompt = PROMPT.format(
            fid=finding["finding_id"],
            category=finding["category"],
            severity=finding["severity"],
            description=finding["description"],
            impact=finding.get("impact", ""),
            evidence_text=evidence_text,
            source_documents=source_documents,
        )

        reasoning, model_error = _ask_model(prompt)

        if reasoning is None:
            validation = {"valid": False, "issues": [model_error]}
        else:
            validation = validate_reasoning(reasoning, finding)

        if validation["valid"]:
            print(f"  {finding['finding_id']}: AI reasoning ACCEPTED")
            finding["ai_reasoning"] = reasoning
            finding["evidence_guard"] = {"status": "PASSED", "issues": []}
        else:
            print(f"  {finding['finding_id']}: AI reasoning REJECTED")
            for issue in validation["issues"]:
                print(f"    - {issue}")
            finding["ai_reasoning"] = create_safe_reasoning(finding)
            finding["evidence_guard"] = {
                "status": "REJECTED_AND_REPLACED",
                "issues": validation["issues"],
            }

    return {"findings": findings}


# ---------------------------------------------------------------
# Node 6: save
# ---------------------------------------------------------------

def save_node(state: FinancialDDState):

    findings = state.get("findings", [])

    save_findings(findings)
    save_metrics(state.get("metrics", []))

    print(f"\n[Save] {len(findings)} finding(s) saved.")

    return {"status": "ANALYSIS_COMPLETE"}


# ---------------------------------------------------------------
# Node 7: human review (graph PAUSES here until the job is resumed)
# ---------------------------------------------------------------

def _pending():
    return [f for f in load_findings() if f.get("status") == "REVIEW_REQUIRED"]


def review_node(state: FinancialDDState):

    pending = _pending()

    if pending:

        print(f"\n[Review] Waiting for human review of {len(pending)} finding(s)...")

        # Pauses the job. Resumed later with Command(resume=...).
        interrupt({
            "awaiting": "human_review",
            "pending": [f["finding_id"] for f in pending],
        })

    return {"findings": load_findings()}


def route_after_review(state: FinancialDDState):

    if _pending():
        return "review"

    if any(f.get("status") == "MORE_EVIDENCE_REQUIRED" for f in load_findings()):
        return "await_evidence"

    return "finish"


# ---------------------------------------------------------------
# Node 8: wait for new documents, then re-analyse
# ---------------------------------------------------------------

def await_evidence_node(state: FinancialDDState):

    print("\n[Evidence] Waiting for new documents...")

    interrupt({"awaiting": "new_documents"})

    # Runs only after the job is resumed.
    reopen_more_evidence()

    documents = extract_all_documents(str(DOCUMENTS_DIR))

    print(f"[Evidence] Reloaded {len(documents)} documents. Re-analysing...")

    return {"documents": documents, "findings": [], "status": "REANALYSING"}


# ---------------------------------------------------------------
# Node 9: finish (report)
# ---------------------------------------------------------------

def finish_node(state: FinancialDDState):

    from reports.report_generator import save_report

    save_report(load_findings(), state.get("documents", []), metrics=load_metrics())

    print("\n[Finish] Review complete. Report generated.")

    return {"findings": load_findings(), "status": "REVIEW_COMPLETE"}


# ---------------------------------------------------------------
# Graph
# ---------------------------------------------------------------

def build_financial_graph(checkpointer=None, human_review=True):
    """human_review=False stops after save (used by analysis-only tests).
    A checkpointer is required for the review pause."""

    graph = StateGraph(FinancialDDState)

    graph.add_node("lead", lead_node)
    graph.add_node("classify", classify_node)
    graph.add_node("completeness", completeness_node)
    graph.add_node("extract", extract_node)
    graph.add_node("checks", checks_node)
    graph.add_node("reason", reason_node)
    graph.add_node("save", save_node)

    graph.add_edge(START, "lead")
    graph.add_conditional_edges(
        "lead", route_after_lead,
        {"classify": "classify", "save": "save"},
    )
    graph.add_edge("classify", "completeness")
    graph.add_conditional_edges(
        "completeness", route_after_completeness,
        {"extract": "extract", "save": "save"},
    )
    graph.add_edge("extract", "checks")
    graph.add_conditional_edges(
        "checks", route_after_checks,
        {"reason": "reason", "save": "save"},
    )
    graph.add_edge("reason", "save")

    if human_review:

        graph.add_node("review", review_node)
        graph.add_node("await_evidence", await_evidence_node)
        graph.add_node("finish", finish_node)

        graph.add_edge("save", "review")
        graph.add_conditional_edges(
            "review", route_after_review,
            {
                "review": "review",
                "await_evidence": "await_evidence",
                "finish": "finish",
            },
        )
        graph.add_edge("await_evidence", "classify")
        graph.add_edge("finish", END)

    else:

        graph.add_edge("save", END)

    return graph.compile(checkpointer=checkpointer)


# ---------------------------------------------------------------
# Financial WORKSTREAM (subgraph used by the DD orchestrator)
# ---------------------------------------------------------------

def build_financial_subgraph():
    """Financial workstream only: classify -> completeness -> extract
    -> checks -> reason. No lead, no save, no human review: the
    orchestrator (workflow/orchestrator.py) owns those."""

    graph = StateGraph(FinancialDDState)

    graph.add_node("classify", classify_node)
    graph.add_node("completeness", completeness_node)
    graph.add_node("extract", extract_node)
    graph.add_node("checks", checks_node)
    graph.add_node("reason", reason_node)

    graph.add_edge(START, "classify")
    graph.add_edge("classify", "completeness")
    graph.add_conditional_edges(
        "completeness", route_after_completeness,
        {"extract": "extract", "save": END},
    )
    graph.add_edge("extract", "checks")
    graph.add_conditional_edges(
        "checks", route_after_checks,
        {"reason": "reason", "save": END},
    )
    graph.add_edge("reason", END)

    return graph.compile()