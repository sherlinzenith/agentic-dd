import sys, shutil, tempfile, pathlib
sys.path.insert(0, ".")

from findings import finding_store as fs
from processing.document_processor import extract_all_documents
import agents.financial_agent as fa
from reports import report_generator as rg

fa._ask_model = lambda prompt: (None, "test: no model")

A, B, C, D = ("01_income_statement.txt", "02_balance_sheet.txt",
              "03_cash_flow_statement.txt", "04_revenue_report.txt")


def run(edits=None):
    edits = edits or {}
    tmp = pathlib.Path(tempfile.mkdtemp())
    fs.RESULTS_DIR = tmp
    fs.FINDINGS_FILE = tmp / "findings.json"
    fs.METRICS_FILE = tmp / "metrics.json"
    d = tmp / "docs"
    d.mkdir()
    for n in (A, B, C, D):
        text = pathlib.Path(f"documents/{n}").read_text(encoding="utf-8-sig")
        if n in edits:
            old, new = edits[n]
            assert old in text, (n, old)
            text = text.replace(old, new)
        (d / n).write_text(text, encoding="utf-8")
    result = fa.build_financial_graph(human_review=False).invoke(
        {"documents": extract_all_documents(str(d)), "findings": [], "status": "STARTED"})

    return result, tmp


def descriptions(result):
    return [f["description"] for f in result["findings"]]


r, tmp = run()
assert len(r["findings"]) == 1 and r["findings"][0]["category"] == "Revenue", descriptions(r)
m = {x["name"]: x["value"] for x in r["metrics"]}
assert m["Gross margin"] == 42.0 and m["Operating margin"] == 15.0 and m["Net margin"] == 9.0, m
assert m["Debt to equity"] == 1.1 and m["Net debt"] == 26.0, m
assert m["Interest cover"] == 5.0 and m["Free cash flow"] == -2.0, m
assert (tmp / "metrics.json").exists()
print("1 ok  baseline: 1 finding + 7 metrics correct")

r, _ = run({B: ("Inventory 12.00", "Inventory 13.00")})
assert any("asset lines" in d for d in descriptions(r)), descriptions(r)
print("2 ok  asset lines vs Total Assets")

r, _ = run({B: ("Long-Term Debt 30.00", "Long-Term Debt 31.00")})
assert any("liability and equity lines" in d for d in descriptions(r)), descriptions(r)
print("3 ok  liability lines vs total")

r, _ = run({C: ("Net Cash from Financing 5.00", "Net Cash from Financing 6.00")})
assert any("do not add up to the Net Change" in d for d in descriptions(r)), descriptions(r)
print("4 ok  cash flow sections vs net change")

r, _ = run({B: ("Cash and Cash Equivalents 18.00", "Cash and Cash Equivalents 17.00")})
f = [x for x in r["findings"] if "Closing Cash in the Cash Flow" in x["description"]]
assert f and {e["document"] for e in f[0]["evidence"]} == {C, B}, descriptions(r)
print("5 ok  closing cash vs balance sheet (2 documents in evidence)")


r, _ = run({C: ("Net Income 9.00", "Net Income 8.00")})
assert any("Net Income in the Cash Flow" in d for d in descriptions(r)), descriptions(r)
print("6 ok  net income vs profit after tax")

r, _ = run({D: ("Q4 FY2025-26 43.00", "Q4 FY2025-26 44.00")})
assert any("sum of the quarterly revenues" in d for d in descriptions(r)), descriptions(r)
print("7 ok  quarterly sum vs total")

r, _ = run({D: ("Reported Annual Revenue 120.00", "Reported Annual Revenue 110.00")})
assert any("management note" in d for d in descriptions(r)), descriptions(r)
print("8 ok  management note vs total")

rg.RESULTS_DIR = tmp
html = rg.generate_report(fs.load_findings(), [], metrics=fs.load_metrics())
assert "Key Metrics" in html and "Gross margin" in html
print("9 ok  report has Key Metrics")

print("ALL CHECK TESTS PASSED")
