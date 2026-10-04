import html
from datetime import datetime
from pathlib import Path

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
REPORT_FILE = RESULTS_DIR / "report.html"

STATUS_LABEL = {
    "REVIEW_REQUIRED": "Pending review",
    "APPROVED": "Approved",
    "REJECTED": "Rejected",
    "MORE_EVIDENCE_REQUIRED": "More evidence required",
}


def _e(value):
    return html.escape(str(value if value is not None else ""))


def generate_report(findings, documents=None, company="AsterNova Technologies Pvt. Ltd.", period="FY 2025-26", metrics=None):
    """Build a self-contained HTML report. Rejected findings are excluded from the body."""

    documents = documents or []
    active = [f for f in findings if f.get("status") != "REJECTED"]
    rejected = [f for f in findings if f.get("status") == "REJECTED"]
    high = [f for f in active if f.get("severity") == "HIGH"]
    pending = [f for f in active if f.get("status") == "REVIEW_REQUIRED"]

    cards = []
    for f in active:
        ev_rows = "".join(
            f"<tr><td>{_e(x.get('document'))}</td><td>{_e(x.get('page'))}</td>"
            f"<td>{_e(x.get('field'))}</td><td>{_e(x.get('value'))}</td></tr>"
            for x in f.get("evidence", [])
        ) or "<tr><td colspan='4'>No evidence attached</td></tr>"

        r = f.get("ai_reasoning") or {}
        reasoning = "".join(
            f"<p><b>{_e(k.replace('_', ' ').title())}:</b> {_e(v)}</p>"
            for k, v in r.items()
        )

        rv = f.get("human_review")
        review = (
            f"<p class='rv'><b>Reviewer:</b> {_e(rv.get('reviewer'))} &middot; "
            f"{_e(rv.get('action'))} &middot; {_e(rv.get('comment'))}</p>"
            if rv else "<p class='rv'>Not yet reviewed.</p>"
        )

        cards.append(f"""
        <div class="card">
          <h3>{_e(f.get('finding_id'))} &mdash; {_e(f.get('category'))}
            <span class="sev {_e(f.get('severity'))}">{_e(f.get('severity'))}</span></h3>
          <p>{_e(f.get('description'))}</p>
          <p><b>Impact:</b> {_e(f.get('impact', '-'))}</p>
          <p><b>Status:</b> {_e(STATUS_LABEL.get(f.get('status'), f.get('status')))}</p>
          <table><tr><th>Document</th><th>Page</th><th>Field</th><th>Value</th></tr>{ev_rows}</table>
          {reasoning}
          {review}
        </div>""")

    doc_list = "".join(f"<li>{_e(d.get('document'))}</li>" for d in documents) or "<li>-</li>"
    rejected_note = (
        f"<p>{len(rejected)} finding(s) were rejected by the reviewer and are not listed.</p>"
        if rejected else ""
    )

    metrics_section = ""
    if metrics:
        rows = "".join(
            f"<tr><td>{_e(m.get('name'))}</td><td>{_e(m.get('value'))} {_e(m.get('unit'))}</td>"
            f"<td>{_e(m.get('formula'))}</td></tr>"
            for m in metrics
        )
        metrics_section = (
            "<h2>3. Key Metrics</h2>"
            "<table><tr><th>Metric</th><th>Value</th><th>Basis</th></tr>"
            + rows + "</table>"
            "<p style='font-size:12px;color:#6b7280'>Calculated from the supplied documents. "
            "Information only; no thresholds are applied.</p>"
        )

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Financial DD Report</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;max-width:900px;margin:30px auto;color:#1f2937}}
h1{{color:#1C7F9F}} h2{{border-bottom:2px solid #1C7F9F;padding-bottom:4px;margin-top:28px}}
.card{{border:1px solid #d1d5db;border-radius:8px;padding:14px 18px;margin:14px 0}}
table{{border-collapse:collapse;width:100%;margin:8px 0}}
th,td{{border:1px solid #d1d5db;padding:6px 8px;text-align:left;font-size:14px}}
th{{background:#f3f4f6}}
.sev{{font-size:12px;padding:2px 8px;border-radius:10px;background:#e5e7eb;margin-left:8px}}
.sev.HIGH{{background:#fee2e2;color:#b91c1c}} .sev.MEDIUM{{background:#fef3c7;color:#92400e}}
.rv{{color:#374151;font-size:14px}}
</style></head><body>
<h1>Financial Due Diligence Report</h1>
<p><b>{_e(company)}</b> &middot; {_e(period)}<br>Generated: {datetime.now().strftime('%d %b %Y %H:%M')}</p>

<h2>1. Summary</h2>
<p>Documents reviewed: {len(documents)} &middot; Findings: {len(active)} &middot;
High severity: {len(high)} &middot; Pending review: {len(pending)}</p>
{rejected_note}

<h2>2. Documents Reviewed</h2><ul>{doc_list}</ul>

{metrics_section}\n<h2>4. Findings</h2>
{''.join(cards) if cards else '<p>No findings.</p>'}

<p style="font-size:12px;color:#6b7280;margin-top:30px">
AI-assisted analysis. Every finding is based on the cited documents and requires human review.</p>
</body></html>"""


def save_report(findings, documents=None, **kwargs):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    content = generate_report(findings, documents, **kwargs)
    REPORT_FILE.write_text(content, encoding="utf-8")
    return content
