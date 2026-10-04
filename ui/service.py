"""Everything the UI needs from the DD engine. No Streamlit code here."""

import html
import json
from datetime import datetime
from pathlib import Path

from agents.inventory import organize, summarize
from agents.readiness import CHECKLISTS
from findings import finding_store as store
from processing.document_processor import extract_document


ROOT = Path(__file__).resolve().parent.parent

WORKSPACE_DIR = ROOT / "documents"

OVERRIDES_FILE = (
    ROOT
    / "results"
    / "classification_overrides.json"
)

UPLOAD_TYPES = [
    "pdf",
    "txt",
]

STEP_LABELS = {
    "inventory": "Documents organized",
    "readiness": "Checked for missing documents",
    "plan": "Investigation planned",
    "financial": "Financial review",
    "legal": "Legal review",
    "cross_domain": "Cross-workstream checks",
    "evidence": "Evidence verified against source pages",
}


# ---------------------------------------------------------------
# Workspace documents
# ---------------------------------------------------------------

def list_files():
    WORKSPACE_DIR.mkdir(
        exist_ok=True
    )

    return sorted(
        f
        for f in WORKSPACE_DIR.iterdir()
        if (
            f.is_file()
            and not f.name.startswith(".")
            and f.suffix.lower().lstrip(".")
            in UPLOAD_TYPES
        )
    )


def read_document(path):
    doc = extract_document(
        str(path)
    )

    if not isinstance(doc, dict):

        doc = {
            "document": Path(path).name,
            "text": str(doc),
            "pages": [str(doc)],
        }

    doc.setdefault(
        "document",
        Path(path).name,
    )

    doc.setdefault(
        "pages",
        [doc.get("text", "")],
    )

    return doc


def load_documents():

    docs = []
    unreadable = []

    for f in list_files():

        try:

            docs.append(
                read_document(f)
            )

        except Exception as error:

            unreadable.append(
                {
                    "document": f.name,
                    "error": str(error),
                }
            )

    return docs, unreadable


def save_uploads(files):
    """Save uploaded files; return one result per file."""

    WORKSPACE_DIR.mkdir(
        exist_ok=True
    )

    results = []

    for file in files:

        target = (
            WORKSPACE_DIR
            / Path(file.name).name
        )

        try:

            target.write_bytes(
                file.getbuffer()
            )

            doc = read_document(
                target
            )

            if not (
                doc.get("text") or ""
            ).strip():

                raise ValueError(
                    "no readable text found"
                )

            results.append(
                {
                    "document": target.name,
                    "ok": True,
                    "pages": len(
                        doc.get("pages") or []
                    ),
                }
            )

        except Exception as error:

            target.unlink(
                missing_ok=True
            )

            results.append(
                {
                    "document": file.name,
                    "ok": False,
                    "error": str(error),
                }
            )

    return results


def remove_document(name):

    safe_name = Path(name).name

    (
        WORKSPACE_DIR
        / safe_name
    ).unlink(
        missing_ok=True
    )

    overrides = load_overrides()

    overrides.pop(
        safe_name,
        None,
    )

    _save_overrides(
        overrides
    )


# ---------------------------------------------------------------
# Organization
# ---------------------------------------------------------------

def load_overrides():

    if not OVERRIDES_FILE.exists():
        return {}

    try:

        data = json.loads(
            OVERRIDES_FILE.read_text(
                encoding="utf-8"
            )
        )

        return data if isinstance(
            data,
            dict,
        ) else {}

    except (
        json.JSONDecodeError,
        OSError,
    ):

        return {}


def _save_overrides(data):

    OVERRIDES_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OVERRIDES_FILE.write_text(
        json.dumps(
            data,
            indent=2,
        ),
        encoding="utf-8",
    )


def set_category(
    name,
    category,
):

    category = str(
        category
    ).strip().lower()

    if category not in {
        "financial",
        "legal",
        "other",
    }:

        raise ValueError(
            f"Invalid workstream category: {category}"
        )

    overrides = load_overrides()

    overrides[
        Path(name).name
    ] = category

    _save_overrides(
        overrides
    )


def organized_workspace():

    docs, unreadable = load_documents()

    rows = organize(
        docs,
        load_overrides(),
    )

    return (
        docs,
        rows,
        summarize(rows),
        unreadable,
    )


def readiness_for(
    rows,
    scope,
):

    out = {}

    for ws in scope:

        items = []

        for label, doc_type in CHECKLISTS.get(
            ws,
            [],
        ):

            match = next(
                (
                    r["document"]
                    for r in rows
                    if (
                        r["type"]
                        == doc_type
                        and r["category"]
                        == ws
                    )
                ),
                None,
            )

            items.append(
                {
                    "item": label,
                    "present": match is not None,
                    "document": match,
                }
            )

        out[ws] = {
            "items": items,
            "missing": [
                i["item"]
                for i in items
                if not i["present"]
            ],
        }

    return out


# ---------------------------------------------------------------
# Investigation
# ---------------------------------------------------------------

def run_investigation(
    dd_types,
):

    from workflow.dd_graph import start_job

    docs, _ = load_documents()

    if not docs:

        raise ValueError(
            "No readable documents are available in the workspace."
        )

    if not dd_types:

        raise ValueError(
            "Select at least one due diligence workstream."
        )

    return start_job(
        dd_types=dd_types,
        documents=docs,
        overrides=load_overrides(),
    )


def latest_job():

    from workflow.dd_graph import (
        job_details,
        latest_job_id,
    )

    job_id = latest_job_id()

    if not job_id:
        return None

    info = job_details(
        job_id
    )

    if not info:
        return None

    if info.get("status") == "NOT_FOUND":
        return None

    return info


def resume(job_id):

    if not job_id:
        raise ValueError(
            "No investigation job is available to resume."
        )

    from workflow.dd_graph import resume_job

    return resume_job(
        job_id
    )


# ---------------------------------------------------------------
# Findings + human review
# ---------------------------------------------------------------

def findings_for(job_id):

    if not job_id:
        return []

    store.set_job(
        job_id
    )

    return store.load_findings()


def metrics_for(job_id):

    if not job_id:
        return []

    store.set_job(
        job_id
    )

    return store.load_metrics()


def review(
    job_id,
    finding_id,
    action,
    reviewer,
    comment,
):

    if not job_id:
        raise ValueError(
            "No active investigation job."
        )

    reviewer = (
        reviewer or ""
    ).strip()

    if not reviewer:

        raise ValueError(
            "Reviewer name is required."
        )

    action = (
        action or ""
    ).strip().upper()

    comment = (
        comment or ""
    ).strip()

    if action in {
        "REJECT",
        "REQUEST_MORE_EVIDENCE",
    } and not comment:

        raise ValueError(
            "A comment is required for this review action."
        )

    store.set_job(
        job_id
    )

    return store.save_review(
        finding_id,
        action,
        reviewer,
        comment,
    )


def page_text(
    documents,
    name,
    page,
):

    if not name:
        return ""

    for d in documents:

        if d.get("document") != name:
            continue

        pages = (
            d.get("pages")
            or [d.get("text", "")]
        )

        try:
            page_no = int(
                page or 1
            )
        except (
            TypeError,
            ValueError,
        ):
            page_no = 1

        if (
            page_no < 1
            or page_no > len(pages)
        ):
            return ""

        return pages[
            page_no - 1
        ]

    return ""


def highlight(
    text,
    value,
):
    """Escape page text and highlight the evidence value."""

    safe = html.escape(
        text or ""
    )

    if value in (
        None,
        "",
    ):

        return safe

    candidates = [
        str(value)
    ]

    if isinstance(
        value,
        (int, float),
    ):

        candidates = [
            f"{value:.2f}",
            f"{value:,.2f}",
            f"{value:g}",
        ]

    for candidate in candidates:

        escaped = html.escape(
            candidate
        )

        if (
            escaped
            and escaped in safe
        ):

            return safe.replace(
                escaped,
                f"<mark>{escaped}</mark>",
                1,
            )

    return safe


def review_counts(
    findings,
):

    c = {
        "total": len(findings),
        "needs_review": 0,
        "approved": 0,
        "rejected": 0,
        "more_evidence": 0,
    }

    for f in findings:

        s = f.get(
            "status"
        )

        if s == "APPROVED":

            c["approved"] += 1

        elif s == "REJECTED":

            c["rejected"] += 1

        elif s == "MORE_EVIDENCE_REQUIRED":

            c["more_evidence"] += 1

        else:

            c["needs_review"] += 1

    return c


# ---------------------------------------------------------------
# Activity
# ---------------------------------------------------------------

def activity_feed(
    job,
    findings,
):

    items = []

    for a in (
        job or {}
    ).get(
        "activity",
        [],
    ):

        step = a.get(
            "step",
            "",
        )

        items.append(
            {
                "at": a.get(
                    "at",
                    "",
                ),
                "title": STEP_LABELS.get(
                    step,
                    step.replace(
                        "_",
                        " ",
                    ).title(),
                ),
                "detail": a.get(
                    "detail",
                    "",
                ),
            }
        )

    for f in findings:

        history = (
            f.get(
                "review_history"
            )
            or []
        )

        current_review = (
            [f["human_review"]]
            if f.get("human_review")
            else []
        )

        for r in history + current_review:

            label = {
                "APPROVE": "approved",
                "REJECT": "rejected",
                "REQUEST_MORE_EVIDENCE": (
                    "requested more evidence on"
                ),
            }.get(
                r.get("action"),
                "reviewed",
            )

            items.append(
                {
                    "at": r.get(
                        "reviewed_at",
                        "",
                    ),
                    "title": (
                        f"{r.get('reviewer', 'Reviewer')} "
                        f"{label} "
                        f"{f.get('finding_id', '')}"
                    ),
                    "detail": (
                        r.get("comment")
                        or f.get(
                            "category",
                            "",
                        )
                    ),
                }
            )

    return sorted(
        items,
        key=lambda i: i.get("at", ""),
        reverse=True,
    )


def fmt_time(iso):

    if not iso:
        return ""

    try:

        value = datetime.fromisoformat(
            iso
        )

        return value.astimezone().strftime(
            "%d %b %Y, %H:%M"
        )

    except (
        ValueError,
        TypeError,
    ):

        return str(iso)


# ---------------------------------------------------------------
# Report
# ---------------------------------------------------------------

def build_report(
    workspace,
    findings,
    metrics,
    rows,
    readiness,
    scope,
):

    e = html.escape

    counts = review_counts(
        findings
    )

    approved = [
        f
        for f in findings
        if f.get("status")
        == "APPROVED"
    ]

    open_items = [
        f
        for f in findings
        if f.get("status")
        in (
            "MORE_EVIDENCE_REQUIRED",
            "REVIEW_REQUIRED",
        )
    ]

    def evidence_li(f):

        out = ""

        for ev in (
            f.get("evidence")
            or []
        ):

            out += (
                "<li>"
                f"{e(str(ev.get('document')))}, "
                f"page {e(str(ev.get('page', '-')))}: "
                f"{e(str(ev.get('field', '')))} "
                f"&mdash; "
                f"{e(str(ev.get('value', '')))}"
                "</li>"
            )

        return (
            out
            or "<li>No document evidence (missing information)</li>"
        )

    def card(f):

        r = (
            f.get("human_review")
            or {}
        )

        return (
            "<div class='f'>"
            "<div class='fh'>"
            f"<b>{e(f.get('finding_id', ''))} "
            f"&middot; "
            f"{e(str(f.get('category', '')))}</b>"
            f"<span class='sev'>"
            f"{e(str(f.get('severity', '')))}"
            f"</span>"
            "</div>"

            f"<p>{e(str(f.get('description', '')))}</p>"

            f"<p class='m'>"
            f"<b>Why it matters:</b> "
            f"{e(str(f.get('impact', '')))}"
            "</p>"

            f"<ul>{evidence_li(f)}</ul>"

            f"<p class='m'>"
            f"Reviewed by "
            f"{e(str(r.get('reviewer', '-')))} "
            f"on "
            f"{e(fmt_time(r.get('reviewed_at', '')))}"
            f"{' &mdash; ' + e(r['comment']) if r.get('comment') else ''}"
            "</p>"

            "</div>"
        )

    sections = ""

    for key, title in (
        (
            "financial",
            "Financial due diligence",
        ),
        (
            "legal",
            "Legal due diligence",
        ),
        (
            "cross_domain",
            "Cross-workstream findings",
        ),
    ):

        group = [
            f
            for f in approved
            if f.get("workstream")
            == key
        ]

        if (
            key == "cross_domain"
            and not group
        ):
            continue

        sections += (
            f"<h2>{title}</h2>"
            + (
                "".join(
                    card(f)
                    for f in group
                )
                or "<p class='m'>No approved findings.</p>"
            )
        )

        if (
            key == "financial"
            and metrics
        ):

            sections += (
                "<h3>Key metrics</h3>"
                "<table>"
                "<tr>"
                "<th>Metric</th>"
                "<th>Value</th>"
                "<th>Basis</th>"
                "</tr>"
                + "".join(
                    (
                        "<tr>"
                        f"<td>{e(str(m.get('name', '')))}</td>"
                        f"<td>{e(str(m.get('value', '')))} "
                        f"{e(str(m.get('unit', '')))}</td>"
                        f"<td>{e(str(m.get('formula', '')))}</td>"
                        "</tr>"
                    )
                    for m in metrics
                )
                + "</table>"
            )

    missing = "".join(
        (
            f"<li>{e(ws.title())}: "
            f"{e(', '.join(r['missing']))}</li>"
        )
        for ws, r in (
            readiness or {}
        ).items()
        if r.get("missing")
    ) or "<li>None</li>"

    open_html = "".join(
        (
            f"<li>{e(f.get('finding_id', ''))} "
            f"&mdash; "
            f"{e(str(f.get('category', '')))} "
            f"("
            f"{'more evidence requested' if f.get('status') == 'MORE_EVIDENCE_REQUIRED' else 'not yet reviewed'}"
            f")</li>"
        )
        for f in open_items
    ) or "<li>None</li>"

    docs_html = "".join(
        (
            "<tr>"
            f"<td>{e(str(r.get('document', '')))}</td>"
            f"<td>{e(str(r.get('category', '')).title())}</td>"
            f"<td>{e(str(r.get('pages', '')))}</td>"
            "</tr>"
        )
        for r in rows
    )

    scope_labels = [
        str(w).title()
        for w in (scope or [])
    ]

    return f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Due Diligence Report</title>

<style>
body {{
    font-family: Inter, Arial, sans-serif;
    max-width: 920px;
    margin: 36px auto;
    color: #1d2730;
    line-height: 1.55;
}}

h1 {{
    color: #23869b;
    margin-bottom: 2px;
}}

h2 {{
    margin-top: 34px;
    border-bottom: 2px solid #e5eaed;
    padding-bottom: 6px;
}}

.m {{
    color: #6b7885;
    font-size: 13px;
}}

.f {{
    border: 1px solid #e5eaed;
    border-left: 4px solid #23869b;
    border-radius: 10px;
    padding: 14px 18px;
    margin: 12px 0;
}}

.fh {{
    display: flex;
    justify-content: space-between;
}}

.sev {{
    font-size: 11px;
    font-weight: 700;
    color: #23869b;
}}

table {{
    border-collapse: collapse;
    width: 100%;
}}

td,
th {{
    border: 1px solid #e5eaed;
    padding: 8px;
    text-align: left;
    font-size: 13px;
}}

th {{
    background: #f4f8fa;
}}

.kpi {{
    display: flex;
    gap: 12px;
}}

.kpi div {{
    flex: 1;
    border: 1px solid #e5eaed;
    border-radius: 10px;
    padding: 12px;
}}

.kpi b {{
    font-size: 22px;
    display: block;
}}
</style>

</head>

<body>

<h1>Due Diligence Report</h1>

<p class="m">
    {e(workspace)}
    &middot;
    {e(', '.join(scope_labels))}
    &middot;
    generated
    {datetime.now().strftime('%d %b %Y, %H:%M')}
</p>

<h2>Executive summary</h2>

<div class="kpi">

<div>
    <b>{len(rows)}</b>
    documents reviewed
</div>

<div>
    <b>{counts['approved']}</b>
    approved findings
</div>

<div>
    <b>{counts['rejected']}</b>
    rejected
</div>

<div>
    <b>{len(open_items)}</b>
    open items
</div>

</div>

<p class="m">
    Only findings approved by a human reviewer are presented
    as conclusions. AI-generated items that were rejected are
    excluded; open items are listed separately.
</p>

{sections}

<h2>Open items</h2>

<ul>
    {open_html}
</ul>

<h2>Missing information</h2>

<ul>
    {missing}
</ul>

<h2>Documents reviewed</h2>

<table>
<tr>
    <th>Document</th>
    <th>Workstream</th>
    <th>Pages</th>
</tr>

{docs_html}

</table>

</body>
</html>
"""