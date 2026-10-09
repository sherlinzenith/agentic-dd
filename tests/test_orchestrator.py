import sys, tempfile, pathlib
sys.path.insert(0, ".")

from langgraph.types import Command
from langgraph.checkpoint.memory import MemorySaver

from findings import finding_store as fs
from processing.document_processor import extract_all_documents
import agents.financial_agent as fa
from workflow.orchestrator import build_dd_graph

fa._ask_model = lambda prompt: (None, "test: no model")

tmp = pathlib.Path(tempfile.mkdtemp())
fs.RESULTS_DIR = tmp
fs.FINDINGS_FILE = tmp / "findings.json"
fs.METRICS_FILE = tmp / "metrics.json"

graph = build_dd_graph(checkpointer=MemorySaver())
docs = extract_all_documents("documents")


def cfg(job):
    return {"configurable": {"thread_id": job}}


def waiting(job):
    s = graph.get_state(cfg(job))
    return s.next[0] if s.next else None


def start(job, types=("financial",)):
    fs.set_job(job)
    fs.reset_findings()
    graph.invoke({"documents": docs, "findings": [], "status": "STARTED",
                  "dd_types": list(types)}, cfg(job))


def test_orchestrator():
    # 1. lead plans, financial workstream runs, job pauses for review
    start("DD-A")
    v = graph.get_state(cfg("DD-A")).values
    assert v["plan"] == ["financial"], v["plan"]
    assert waiting("DD-A") == "review"
    assert v["findings"] and all(f["workstream"] == "financial" for f in v["findings"])
    assert all(f["job_id"] == "DD-A" for f in v["findings"])
    assert len([f for f in v["findings"] if f["category"] == "Revenue"]) == 1
    print("1 ok  lead -> financial workstream -> merge -> review pause")

    # 2. a second job does not touch the first job's findings
    start("DD-B")
    assert waiting("DD-B") == "review"
    fs.set_job("DD-A"); a = fs.load_findings()
    fs.set_job("DD-B"); b = fs.load_findings()
    assert a and b and (tmp / "jobs" / "DD-A" / "findings.json").exists()
    assert (tmp / "jobs" / "DD-B" / "findings.json").exists()
    print("2 ok  two jobs -> two separate findings files")

    # 3. approving job A leaves job B pending
    fs.set_job("DD-A")
    for f in fs.load_findings():
        fs.save_review(f["finding_id"], "APPROVE", "t", "ok")
    graph.invoke(Command(resume=True), cfg("DD-A"))
    assert waiting("DD-A") is None
    assert graph.get_state(cfg("DD-A")).values["status"] == "REVIEW_COMPLETE"
    fs.set_job("DD-B")
    assert all(f["status"] == "REVIEW_REQUIRED" for f in fs.load_findings())
    assert waiting("DD-B") == "review"
    print("3 ok  approve job A -> complete; job B still waiting")

    # 4. financial + legal run together, findings tagged by workstream
    start("DD-C", ("legal", "financial"))
    v = graph.get_state(cfg("DD-C")).values
    assert v["plan"] == ["legal", "financial"], v["plan"]
    by_ws = {}
    for f in v["findings"]:
        by_ws.setdefault(f["workstream"], []).append(f["finding_id"])
    assert set(by_ws) == {"financial", "legal", "cross_domain"}, by_ws
    assert all(i.startswith("FIN-") for i in by_ws["financial"])
    assert all(i.startswith("LEG-") for i in by_ws["legal"])
    assert any(f["category"] == "Change of Control" for f in v["findings"])
    assert waiting("DD-C") == "review"
    print("4 ok  financial + legal in one job, findings tagged by workstream")

    # 5. new pipeline stages: inventory, readiness, cross-domain, evidence verification
    v = graph.get_state(cfg("DD-C")).values
    inv = {r["document"]: r for r in v["inventory"]}
    assert inv["05_customer_agreement.txt"]["category"] == "legal"
    assert inv["01_income_statement.txt"]["category"] == "financial"
    assert v["inventory_summary"]["total"] == len(docs)
    print("5 ok  inventory classifies every document")

    fin_r = v["readiness"]["financial"]
    assert fin_r["score"] <= 100 and "items" in fin_r
    assert v["readiness"]["legal"]["score"] == 100
    print("6 ok  readiness scores computed, legal complete")

    cross = [f for f in v["findings"] if f["workstream"] == "cross_domain"]
    assert cross and all(f["finding_id"].startswith("CRS-") for f in cross)
    assert all(len(f["related_findings"]) == 2 for f in cross)
    print("7 ok  cross-domain findings link financial + legal:", [f["finding_id"] for f in cross])

    for f in v["findings"]:
        assert "evidence_verification" in f, f["finding_id"]
    rev = next(f for f in v["findings"] if f["category"] == "Revenue")
    assert rev["evidence_verification"]["status"] == "VERIFIED", rev["evidence_verification"]
    coc = next(f for f in v["findings"] if f["category"] == "Change of Control")
    assert coc["evidence_verification"]["status"] == "VERIFIED"
    print("8 ok  evidence verified against real pages")

    steps = [a["step"] for a in v["activity"]]
    order = ["inventory", "readiness", "plan"]
    assert steps[:3] == order and "cross_domain" in steps and steps.index("evidence") > steps.index("cross_domain")
    print("9 ok  activity timeline in the right order:", steps)

    # 10. evidence that is NOT on the page is flagged, not trusted
    from agents.evidence_verify import verify_finding
    bad = {"evidence": [{"document": "05_customer_agreement.txt", "page": 1, "field": "x", "value": "this clause does not exist"}]}
    assert verify_finding(bad, {d["document"]: d for d in docs})["status"] == "UNVERIFIED"
    print("10 ok  fabricated evidence flagged UNVERIFIED")

    # 11. each workstream receives ONLY its own documents
    from workflow.orchestrator import fan_out
    from agents.inventory import organize
    state = {"documents": docs, "plan": ["financial", "legal"], "inventory": organize(docs)}
    sends = {s.node: [d["document"] for d in s.arg["documents"]] for s in fan_out(state)}
    assert "05_customer_agreement.txt" not in sends["financial_ws"], sends
    assert "05_customer_agreement.txt" in sends["legal_ws"], sends
    print("11 ok  financial gets only financial docs, legal only contracts")

    # 12. a reviewer can move a document to another workstream
    rows = {r["document"]: r for r in organize(docs, {"04_revenue_report.txt": "other"})}
    assert rows["04_revenue_report.txt"]["category"] == "other" and rows["04_revenue_report.txt"]["manual"]
    state["inventory"] = list(rows.values())
    sends = {s.node: [d["document"] for d in s.arg["documents"]] for s in fan_out(state)}
    assert "04_revenue_report.txt" not in sends["financial_ws"]
    print("12 ok  manual category override respected by the workstreams")

    print("ALL ORCHESTRATOR TESTS PASSED")


if __name__ == "__main__":
    test_orchestrator()

