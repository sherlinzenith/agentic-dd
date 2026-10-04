import sys, shutil, tempfile, pathlib
sys.path.insert(0, ".")
try:
    import langgraph.graph  # real one on your machine
except ImportError:
    sys.path.insert(0, "tests/fake"); import langgraph_shim  # offline shim

from findings import finding_store as fs
from processing.document_processor import extract_all_documents
import agents.financial_agent as fa

# never load Qwen in tests: return unsafe text so the Evidence Guard must replace it
fa._ask_model = lambda prompt: ({
    "issue": "potential error in revenue", "why_it_matters": "fraud",
    "what_should_be_reviewed": "x", "evidence_conclusion": "y"}, None)

def run(files):
    tmp = pathlib.Path(tempfile.mkdtemp())
    fs.RESULTS_DIR = tmp; fs.FINDINGS_FILE = tmp / "f.json"
    d = tmp / "docs"; d.mkdir()
    for src, dst in files.items():
        shutil.copy(f"documents/{src}", d / dst)
    docs = extract_all_documents(str(d))
    return fa.build_financial_graph(human_review=False).invoke(
        {"documents": docs, "findings": [], "status": "STARTED"})

A, B, C, D = ("01_income_statement.txt", "02_balance_sheet.txt",
              "03_cash_flow_statement.txt", "04_revenue_report.txt")

# 1. original names -> FIN-001 revenue mismatch, guard replaces unsafe AI text
r = run({A: A, B: B, C: C, D: D})
f = r["findings"]
assert len(f) == 1 and f[0]["finding_id"] == "FIN-001" and f[0]["category"] == "Revenue", f
assert f[0]["evidence_guard"]["status"] == "REJECTED_AND_REPLACED"
assert "20.00" in f[0]["ai_reasoning"]["evidence_conclusion"]
print("1 ok  original names -> FIN-001")

# 2. renamed files (no hints in the name) -> same result, real names in evidence
r = run({A: "FS_2025.txt", B: "x1.txt", C: "x2.txt", D: "report_final.txt"})
f = r["findings"]
assert len(f) == 1 and f[0]["category"] == "Revenue"
assert {e["document"] for e in f[0]["evidence"]} == {"FS_2025.txt", "report_final.txt"}
print("2 ok  renamed files -> same finding, evidence uses real names")

# 3. missing balance sheet -> missing-document finding, no crash
r = run({A: A, C: C, D: D})
cats = [x["category"] for x in r["findings"]]
assert cats[0] == "Missing Document" and "Revenue" in cats, cats
print("3 ok  missing doc ->", cats)

# 4. nothing usable -> goes straight to save
r = run({A: A})
assert r["status"] == "ANALYSIS_COMPLETE"
print("4 ok  single doc handled ->", [x["category"] for x in r["findings"]])

# 5. clean data (revenue report fixed to 100) -> only no findings
tmp = pathlib.Path(tempfile.mkdtemp()); (tmp / "d").mkdir()
for n in (A, B, C): shutil.copy(f"documents/{n}", tmp / "d" / n)
(tmp / "d" / D).write_text(pathlib.Path(f"documents/{D}").read_text().replace("120.00", "100.00").replace("43.00", "23.00"))
fs.RESULTS_DIR = tmp; fs.FINDINGS_FILE = tmp / "f.json"
r = fa.build_financial_graph(human_review=False).invoke({"documents": extract_all_documents(str(tmp / "d")), "findings": [], "status": "STARTED"})
assert r["findings"] == [], r["findings"]
print("5 ok  clean data -> no findings")
print("ALL TESTS PASSED")
