import sys, tempfile, pathlib
sys.path.insert(0, ".")

from findings import finding_store as fs
from processing.document_processor import extract_all_documents
import agents.financial_agent as fa
from agents.lead_agent import lead_node, route_after_lead, plan_types

fa._ask_model = lambda prompt: (None, "test: no model")

def test_lead():
    assert plan_types(["Financial"]) == ["financial"]
    assert plan_types(["legal", "financial", "financial"]) == ["financial"]
    try:
        plan_types(["legal"])
        raise SystemExit("legal-only should have failed")
    except ValueError:
        pass

    out = lead_node({"dd_types": ["legal", "financial"]})
    assert out["plan"] == ["financial"] and any("legal" in n for n in out["lead_notes"])
    assert route_after_lead(out) == "classify"
    assert lead_node({})["plan"] == ["financial"]
    print("1 ok  lead agent plans and skips unavailable types")

    tmp = pathlib.Path(tempfile.mkdtemp())
    fs.RESULTS_DIR = tmp
    fs.FINDINGS_FILE = tmp / "findings.json"
    fs.METRICS_FILE = tmp / "metrics.json"

    r = fa.build_financial_graph(human_review=False).invoke({
        "documents": extract_all_documents("documents"),

        "findings": [], "status": "STARTED",
        "dd_types": ["legal", "financial"],
    })
    assert r["plan"] == ["financial"] and len(r["findings"]) == 1, r
    print("2 ok  graph runs the Financial agent through the lead agent")

    print("ALL LEAD TESTS PASSED")


if __name__ == "__main__":
    test_lead()

