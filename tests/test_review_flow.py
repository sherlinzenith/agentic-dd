import sys, shutil, tempfile, pathlib
sys.path.insert(0, ".")

from langgraph.types import Command
from langgraph.checkpoint.memory import MemorySaver

from findings import finding_store as fs
from processing.document_processor import extract_all_documents
import agents.financial_agent as fa
from reports import report_generator as rg

# Qwen is never loaded in tests
fa._ask_model = lambda prompt: (None, "test: no model")

A, B, C, D = ("01_income_statement.txt", "02_balance_sheet.txt",
              "03_cash_flow_statement.txt", "04_revenue_report.txt")

# isolated results + documents folders
tmp = pathlib.Path(tempfile.mkdtemp())
fs.RESULTS_DIR = tmp
fs.FINDINGS_FILE = tmp / "findings.json"
rg.RESULTS_DIR = tmp
rg.REPORT_FILE = tmp / "report.html"
docs = tmp / "docs"
docs.mkdir()
for n in (A, B, C, D):
    shutil.copy(f"documents/{n}", docs / n)
fa.DOCUMENTS_DIR = docs

graph = fa.build_financial_graph(checkpointer=MemorySaver())
cfg = {"configurable": {"thread_id": "DD-TEST"}}



def waiting():
    snap = graph.get_state(cfg)
    return snap.next[0] if snap.next else None


# 1. analysis runs, then the job PAUSES for human review
graph.invoke({"documents": extract_all_documents(str(docs)), "findings": [], "status": "STARTED"}, cfg)
assert waiting() == "review", waiting()
assert fs.load_findings()[0]["status"] == "REVIEW_REQUIRED"
print("1 ok  job paused for human review")

# 2. resume without reviewing -> still paused
graph.invoke(Command(resume=True), cfg)
assert waiting() == "review"
print("2 ok  resume with no decision -> still paused")

# 3. reviewer asks for more evidence -> job waits for new documents
fs.save_review("FIN-001", "REQUEST_MORE_EVIDENCE", "sherlin", "need reconciliation")
graph.invoke(Command(resume=True), cfg)
assert waiting() == "await_evidence", waiting()
print("3 ok  more evidence requested -> waiting for documents")

# 4. corrected revenue report uploaded -> re-analysis -> clean -> finished
text = pathlib.Path(docs / D).read_text(encoding="utf-8-sig")
(docs / D).write_text(text.replace("120.00", "100.00").replace("43.00", "23.00"), encoding="utf-8")
graph.invoke(Command(resume=True), cfg)
assert waiting() is None, waiting()
assert graph.get_state(cfg).values["status"] == "REVIEW_COMPLETE"
assert fs.load_findings() == []
assert (tmp / "report.html").exists()

print("4 ok  new document -> re-analysis clean -> REVIEW_COMPLETE + report")

# 5. approve path on a fresh job
shutil.copy(f"documents/{D}", docs / D)
cfg2 = {"configurable": {"thread_id": "DD-TEST-2"}}
graph.invoke({"documents": extract_all_documents(str(docs)), "findings": [], "status": "STARTED"}, cfg2)
assert graph.get_state(cfg2).next[0] == "review"
fs.save_review("FIN-001", "APPROVE", "sherlin", "confirmed")
graph.invoke(Command(resume=True), cfg2)
assert not graph.get_state(cfg2).next
assert graph.get_state(cfg2).values["status"] == "REVIEW_COMPLETE"
html = (tmp / "report.html").read_text(encoding="utf-8")
assert "FIN-001" in html and "Approved" in html
print("5 ok  approve -> REVIEW_COMPLETE, report contains approved finding")

print("ALL REVIEW-FLOW TESTS PASSED")
