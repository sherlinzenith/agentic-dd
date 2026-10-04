from __future__ import annotations

import streamlit as st
from pathlib import Path
from datetime import datetime


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Due Diligence",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# IMPORT EXISTING DD SERVICE
# ============================================================

from ui import service


# ============================================================
# SESSION STATE
# ============================================================

DEFAULT_STATE = {
    "page": "Overview",
    "selected_job": None,
    "run_started": False,
    "reviewer": "Human Reviewer",
}

for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# CSS
# IMPORTANT:
# CSS is injected through st.markdown with unsafe_allow_html.
# It is NEVER displayed as user-facing text.
# ============================================================

CSS = """
<style>

:root {
    --bg: #f6f8fb;
    --surface: #ffffff;
    --surface-soft: #f9fafc;
    --border: #e6eaf0;
    --text: #18212f;
    --muted: #6b7280;
    --primary: #246b8f;
    --primary-soft: #eaf4f8;
    --green: #14805e;
    --green-soft: #eaf7f2;
    --orange: #b7791f;
    --orange-soft: #fff7e8;
    --red: #c0392b;
    --red-soft: #fff0ef;
    --shadow: 0 3px 18px rgba(24, 33, 47, 0.06);
}

html, body, [class*="css"] {
    font-family:
        Inter,
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;
}

.stApp {
    background: var(--bg);
}

/* Hide Streamlit branding */
#MainMenu {
    visibility: hidden;
}

footer {
    visibility: hidden;
}

header {
    visibility: hidden;
}

/* Sidebar */

section[data-testid="stSidebar"] {
    background: #ffffff;
    border-right: 1px solid var(--border);
}

section[data-testid="stSidebar"] > div {
    padding-top: 1.5rem;
}

/* Buttons */

.stButton > button {
    border-radius: 9px;
    min-height: 40px;
    font-weight: 600;
    border: 1px solid var(--border);
    background: white;
}

.stButton > button:hover {
    border-color: var(--primary);
    color: var(--primary);
}

/* Primary buttons */

.stButton > button[kind="primary"] {
    background: var(--primary);
    color: white;
    border-color: var(--primary);
}

/* Metrics */

[data-testid="stMetric"] {
    background: white;
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 16px;
    box-shadow: var(--shadow);
}

[data-testid="stMetricLabel"] {
    color: var(--muted);
}

[data-testid="stMetricValue"] {
    color: var(--text);
}

/* Expanders */

[data-testid="stExpander"] {
    border: 1px solid var(--border);
    border-radius: 12px;
    background: white;
}

/* Tabs */

button[data-baseweb="tab"] {
    font-weight: 600;
}

/* Cards */

.dd-card {
    background: white;
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 20px;
    margin-bottom: 14px;
    box-shadow: var(--shadow);
}

.dd-card-title {
    font-size: 17px;
    font-weight: 700;
    color: var(--text);
    margin-bottom: 6px;
}

.dd-card-text {
    font-size: 14px;
    line-height: 1.6;
    color: var(--muted);
}

.dd-section-title {
    font-size: 22px;
    font-weight: 750;
    color: var(--text);
    margin-top: 8px;
    margin-bottom: 5px;
}

.dd-section-subtitle {
    color: var(--muted);
    font-size: 14px;
    margin-bottom: 22px;
}

.hero {
    background: linear-gradient(
        135deg,
        #eaf4f8 0%,
        #f8fbfd 100%
    );
    border: 1px solid #dcecf2;
    border-radius: 18px;
    padding: 30px;
    margin-bottom: 22px;
}

.hero-title {
    font-size: 30px;
    font-weight: 800;
    color: var(--text);
    margin-bottom: 8px;
}

.hero-text {
    color: var(--muted);
    font-size: 15px;
    line-height: 1.7;
    max-width: 800px;
}

.badge {
    display: inline-block;
    border-radius: 20px;
    padding: 5px 10px;
    font-size: 12px;
    font-weight: 700;
    margin-right: 6px;
}

.badge-green {
    background: var(--green-soft);
    color: var(--green);
}

.badge-orange {
    background: var(--orange-soft);
    color: var(--orange);
}

.badge-red {
    background: var(--red-soft);
    color: var(--red);
}

.badge-blue {
    background: var(--primary-soft);
    color: var(--primary);
}

.finding {
    background: white;
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 20px;
    margin-bottom: 14px;
}

.finding-title {
    font-size: 16px;
    font-weight: 700;
    color: var(--text);
}

.finding-meta {
    font-size: 12px;
    color: var(--muted);
    margin-top: 5px;
}

.evidence {
    background: #f8fafc;
    border-left: 3px solid var(--primary);
    border-radius: 6px;
    padding: 12px 14px;
    margin-top: 12px;
    font-size: 13px;
    color: #374151;
}

.timeline {
    border-left: 2px solid #dce3ea;
    margin-left: 10px;
    padding-left: 22px;
}

.timeline-item {
    position: relative;
    margin-bottom: 24px;
}

.timeline-dot {
    position: absolute;
    left: -30px;
    top: 3px;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: var(--primary);
}

.timeline-title {
    font-weight: 700;
    color: var(--text);
}

.timeline-detail {
    font-size: 13px;
    color: var(--muted);
    margin-top: 3px;
}

.step {
    padding: 13px 15px;
    border-radius: 10px;
    margin-bottom: 8px;
    border: 1px solid var(--border);
    background: white;
}

.step-active {
    border-color: var(--primary);
    background: var(--primary-soft);
}

.step-done {
    border-color: #cfe9de;
    background: var(--green-soft);
}

.step-number {
    display: inline-block;
    width: 25px;
    height: 25px;
    border-radius: 50%;
    text-align: center;
    padding-top: 3px;
    margin-right: 8px;
    font-weight: 700;
    background: #e9edf2;
}

.step-done .step-number {
    background: var(--green);
    color: white;
}

.step-active .step-number {
    background: var(--primary);
    color: white;
}

.workspace-empty {
    text-align: center;
    padding: 55px 25px;
    background: white;
    border: 1px dashed #cfd7df;
    border-radius: 16px;
}

.workspace-empty-title {
    font-size: 19px;
    font-weight: 700;
    margin-bottom: 8px;
}

.workspace-empty-text {
    color: var(--muted);
    font-size: 14px;
}

</style>
"""

st.markdown(CSS, unsafe_allow_html=True)


# ============================================================
# SAFE UI HELPERS
# ============================================================

def card(title: str, text: str):
    """
    Render a visual card.

    IMPORTANT:
    This function itself renders the HTML.
    We never print the HTML string.
    """
    st.markdown(
        f"""
        <div class="dd-card">
            <div class="dd-card-title">{title}</div>
            <div class="dd-card-text">{text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_badge(status: str) -> str:
    status = (status or "").upper()

    if status == "APPROVED":
        return '<span class="badge badge-green">Approved</span>'

    if status == "REJECTED":
        return '<span class="badge badge-red">Rejected</span>'

    if status == "MORE_EVIDENCE_REQUIRED":
        return '<span class="badge badge-orange">More evidence required</span>'

    return '<span class="badge badge-blue">Needs review</span>'


def safe_value(value, fallback="—"):
    if value is None:
        return fallback

    if isinstance(value, dict):
        return ", ".join(
            f"{k}: {v}"
            for k, v in value.items()
        )

    if isinstance(value, list):
        return ", ".join(str(x) for x in value)

    return str(value)


def render_header(title, subtitle):
    st.markdown(
        f"""
        <div class="dd-section-title">{title}</div>
        <div class="dd-section-subtitle">{subtitle}</div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown(
        """
        <div style="
            font-size:22px;
            font-weight:800;
            margin-bottom:4px;
            color:#18212f;
        ">
            Due Diligence
        </div>

        <div style="
            font-size:12px;
            color:#6b7280;
            margin-bottom:25px;
        ">
            AI-assisted deal investigation
        </div>
        """,
        unsafe_allow_html=True,
    )

    pages = [
        ("Overview", "Overview"),
        ("Documents", "Documents"),
        ("Investigation", "Investigation"),
        ("Review", "Review"),
        ("Report", "Report"),
        ("Activity", "Activity"),
    ]

    for label, page in pages:

        if st.button(
            label,
            key=f"nav_{page}",
            use_container_width=True,
        ):
            st.session_state.page = page

    st.divider()

    st.caption("Reviewer")

    st.session_state.reviewer = st.text_input(
        "Reviewer name",
        value=st.session_state.reviewer,
        label_visibility="collapsed",
    )


# ============================================================
# LOAD CURRENT DATA
# ============================================================

try:
    documents, rows, summary, unreadable = service.organized_workspace()
except Exception as error:
    documents = []
    rows = []
    summary = {}
    unreadable = [
        {
            "document": "Workspace",
            "error": str(error),
        }
    ]

job = service.latest_job()

job_id = None

if job:
    job_id = job.get("job_id")

findings = []

if job_id:
    try:
        findings = service.findings_for(job_id)
    except Exception:
        findings = []

metrics = []

if job_id:
    try:
        metrics = service.metrics_for(job_id)
    except Exception:
        metrics = []


# ============================================================
# OVERVIEW
# ============================================================

if st.session_state.page == "Overview":

    st.markdown(
        """
        <div class="hero">

            <div class="hero-title">
                Due Diligence Workspace
            </div>

            <div class="hero-text">
                Organize deal documents, run structured due diligence,
                review AI-generated findings with evidence, and produce
                a review-ready report.
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    total_docs = len(documents)

    financial_docs = len(
        [
            r for r in rows
            if r.get("category") == "financial"
        ]
    )

    legal_docs = len(
        [
            r for r in rows
            if r.get("category") == "legal"
        ]
    )

    counts = service.review_counts(findings)

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Documents",
        total_docs,
    )

    c2.metric(
        "Financial",
        financial_docs,
    )

    c3.metric(
        "Legal",
        legal_docs,
    )

    c4.metric(
        "Needs review",
        counts["needs_review"],
    )

    st.markdown("<br>", unsafe_allow_html=True)

    left, right = st.columns([1.35, 1])

    with left:

        render_header(
            "Investigation workflow",
            "Follow the deal from document intake through final review.",
        )

        steps = [
            ("Documents", "Collect and organize source documents"),
            ("Organization", "Classify documents into DD workstreams"),
            ("Investigation", "Run selected specialist reviews"),
            ("Evidence", "Verify findings against source documents"),
            ("Human review", "Approve, reject, or request evidence"),
            ("Report", "Generate the final diligence output"),
        ]

        for index, (title, text_value) in enumerate(steps):

            done = False
            active = False

            if index == 0 and total_docs:
                done = True

            elif index == 1 and rows:
                done = True

            elif index == 2 and job:
                done = True

            elif index == 3 and job:
                done = True

            elif index == 4 and findings:
                active = True

            html_class = "step"

            if done:
                html_class += " step-done"

            elif active:
                html_class += " step-active"

            st.markdown(
                f"""
                <div class="{html_class}">
                    <span class="step-number">
                        {index + 1}
                    </span>
                    <strong>{title}</strong>
                    <div style="
                        margin-left:38px;
                        color:#6b7280;
                        font-size:13px;
                        margin-top:3px;
                    ">
                        {text_value}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with right:

        render_header(
            "What happens next?",
            "The platform keeps the investigation structured.",
        )

        card(
            "1. Organize",
            "Documents are identified and grouped into the relevant due diligence workstreams.",
        )

        card(
            "2. Investigate",
            "Specialist agents analyze only the documents relevant to their workstream.",
        )

        card(
            "3. Review evidence",
            "Findings are linked back to supporting source information before they enter human review.",
        )

        card(
            "4. Approve findings",
            "A reviewer can approve, reject, or request additional evidence.",
        )


# ============================================================
# DOCUMENTS
# ============================================================

elif st.session_state.page == "Documents":

    render_header(
        "Documents",
        "Your deal workspace and source documents.",
    )

    upload_files = st.file_uploader(
        "Upload deal documents",
        type=["pdf", "txt"],
        accept_multiple_files=True,
        help="Upload financial statements, contracts, reports, and other deal documents.",
    )

    if upload_files:

        if st.button(
            "Add documents to workspace",
            type="primary",
        ):

            results = service.save_uploads(upload_files)

            success = sum(
                1 for r in results
                if r.get("ok")
            )

            if success:
                st.success(
                    f"{success} document(s) added successfully."
                )

            for result in results:

                if not result.get("ok"):
                    st.error(
                        f"{result.get('document')}: "
                        f"{result.get('error')}"
                    )

            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    if not documents:

        st.markdown(
            """
            <div class="workspace-empty">

                <div class="workspace-empty-title">
                    No documents in this workspace
                </div>

                <div class="workspace-empty-text">
                    Upload the deal documents above to begin
                    the due diligence workflow.
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

    else:

        st.write(
            f"**{len(documents)} documents** available for investigation."
        )

        for doc in documents:

            name = doc.get("document", "Unknown document")

            row = next(
                (
                    r for r in rows
                    if r.get("document") == name
                ),
                {},
            )

            category = row.get(
                "category",
                "unclassified",
            )

            doc_type = row.get(
                "type",
                "Document",
            )

            with st.container():

                col1, col2, col3 = st.columns(
                    [5, 2, 1]
                )

                with col1:
                    st.markdown(
                        f"**{name}**"
                    )

                    st.caption(
                        f"{doc_type} · "
                        f"{category.title()}"
                    )

                with col2:
                    if category == "financial":
                        st.success(
                            "Financial"
                        )
                    elif category == "legal":
                        st.info(
                            "Legal"
                        )
                    else:
                        st.warning(
                            "Unclassified"
                        )

                with col3:

                    if st.button(
                        "Remove",
                        key=f"remove_{name}",
                    ):

                        service.remove_document(name)
                        st.rerun()

                st.divider()


# ============================================================
# INVESTIGATION
# ============================================================

elif st.session_state.page == "Investigation":

    render_header(
        "Investigation",
        "Choose the due diligence workstreams to run.",
    )

    if not documents:

        st.warning(
            "Upload documents before starting an investigation."
        )

    else:

        st.markdown(
            """
            <div class="dd-card">

                <div class="dd-card-title">
                    Select investigation areas
                </div>

                <div class="dd-card-text">
                    The Lead Agent will use your selection to
                    create the investigation plan and route the
                    relevant documents to specialist agents.
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

        financial = st.checkbox(
            "Financial Due Diligence",
            value=True,
        )

        legal = st.checkbox(
            "Legal Due Diligence",
            value=False,
        )

        st.markdown("<br>", unsafe_allow_html=True)

        selected = []

        if financial:
            selected.append("financial")

        if legal:
            selected.append("legal")

        st.markdown(
            f"**Selected workstreams:** "
            f"{', '.join(x.title() for x in selected) if selected else 'None'}"
        )

        if st.button(
            "Start Due Diligence",
            type="primary",
            use_container_width=False,
        ):

            if not selected:

                st.warning(
                    "Select at least one workstream."
                )

            else:

                with st.spinner(
                    "Preparing the due diligence investigation..."
                ):

                    try:

                        result = service.run_investigation(
                            selected
                        )

                        new_job_id = (
                            result.get("job_id")
                            if isinstance(result, dict)
                            else None
                        )

                        if new_job_id:
                            st.session_state.selected_job = (
                                new_job_id
                            )

                        st.session_state.run_started = True

                        st.success(
                            "Investigation started successfully."
                        )

                        st.session_state.page = "Review"

                        st.rerun()

                    except Exception as error:

                        st.error(
                            f"Unable to start investigation: {error}"
                        )

        if job:

            st.markdown("<br>", unsafe_allow_html=True)

            card(
                "Current investigation",
                f"Job {job.get('job_id', '—')} · "
                f"Status: {job.get('status', '—')}",
            )


# ============================================================
# REVIEW
# ============================================================

elif st.session_state.page == "Review":

    render_header(
        "Human Review",
        "Review AI-generated findings against their supporting evidence.",
    )

    counts = service.review_counts(findings)

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Total findings",
        counts["total"],
    )

    c2.metric(
        "Needs review",
        counts["needs_review"],
    )

    c3.metric(
        "Approved",
        counts["approved"],
    )

    c4.metric(
        "More evidence",
        counts["more_evidence"],
    )

    st.markdown("<br>", unsafe_allow_html=True)

    if not findings:

        st.markdown(
            """
            <div class="workspace-empty">

                <div class="workspace-empty-title">
                    No findings are ready for review
                </div>

                <div class="workspace-empty-text">
                    Start an investigation to generate findings.
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

    else:

        for index, finding in enumerate(findings):

            finding_id = finding.get(
                "finding_id",
                f"finding-{index}",
            )

            title = finding.get(
                "description"
            ) or finding.get(
                "title"
            ) or "Due diligence finding"

            status = finding.get(
                "status",
                "NEEDS_REVIEW",
            )

            workstream = finding.get(
                "workstream",
                finding.get(
                    "category",
                    "General",
                ),
            )

            st.markdown(
                f"""
                <div class="finding">

                    <div class="finding-title">
                        {title}
                    </div>

                    <div class="finding-meta">
                        {workstream.title()}
                        &nbsp; · &nbsp;
                        {status_badge(status)}
                    </div>

                </div>
                """,
                unsafe_allow_html=True,
            )

            with st.expander(
                "View finding details",
                expanded=True,
            ):

                explanation = (
                    finding.get("reasoning")
                    or finding.get("explanation")
                    or finding.get("summary")
                )

                if explanation:
                    st.markdown(
                        "**Finding explanation**"
                    )
                    st.write(
                        safe_value(explanation)
                    )

                evidence = finding.get(
                    "evidence"
                )

                if evidence:

                    st.markdown(
                        "**Supporting evidence**"
                    )

                    if isinstance(
                        evidence,
                        list,
                    ):

                        for ev in evidence:

                            if isinstance(ev, dict):

                                document = ev.get(
                                    "document",
                                    "Source document",
                                )

                                page = ev.get(
                                    "page",
                                    "—",
                                )

                                quote = (
                                    ev.get("quote")
                                    or ev.get("text")
                                    or ev.get("value")
                                    or ""
                                )

                                st.markdown(
                                    f"""
                                    <div class="evidence">

                                        <strong>
                                            {document}
                                        </strong>

                                        · Page {page}

                                        <br><br>

                                        {quote}

                                    </div>
                                    """,
                                    unsafe_allow_html=True,
                                )

                            else:

                                st.write(
                                    safe_value(ev)
                                )

                    elif isinstance(
                        evidence,
                        dict,
                    ):

                        document = evidence.get(
                            "document",
                            "Source document",
                        )

                        page = evidence.get(
                            "page",
                            "—",
                        )

                        quote = (
                            evidence.get("quote")
                            or evidence.get("text")
                            or ""
                        )

                        st.markdown(
                            f"""
                            <div class="evidence">

                                <strong>
                                    {document}
                                </strong>

                                · Page {page}

                                <br><br>

                                {quote}

                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                    else:

                        st.write(
                            safe_value(evidence)
                        )

                st.markdown("---")

                if status not in {
                    "APPROVED",
                    "REJECTED",
                }:

                    col1, col2, col3 = st.columns(3)

                    with col1:

                        if st.button(
                            "Approve",
                            key=f"approve_{finding_id}",
                            type="primary",
                        ):

                            try:

                                service.review(
                                    job_id,
                                    finding_id,
                                    "APPROVE",
                                    st.session_state.reviewer,
                                    "Approved after human review.",
                                )

                                st.success(
                                    "Finding approved."
                                )

                                st.rerun()

                            except Exception as error:

                                st.error(
                                    str(error)
                                )

                    with col2:

                        if st.button(
                            "Reject",
                            key=f"reject_{finding_id}",
                        ):

                            try:

                                service.review(
                                    job_id,
                                    finding_id,
                                    "REJECT",
                                    st.session_state.reviewer,
                                    "Rejected after human review.",
                                )

                                st.success(
                                    "Finding rejected."
                                )

                                st.rerun()

                            except Exception as error:

                                st.error(
                                    str(error)
                                )

                    with col3:

                        if st.button(
                            "Request evidence",
                            key=f"evidence_{finding_id}",
                        ):

                            try:

                                service.review(
                                    job_id,
                                    finding_id,
                                    "REQUEST_MORE_EVIDENCE",
                                    st.session_state.reviewer,
                                    "Additional supporting evidence required.",
                                )

                                st.success(
                                    "Additional evidence requested."
                                )

                                st.rerun()

                            except Exception as error:

                                st.error(
                                    str(error)
                                )


# ============================================================
# REPORT
# ============================================================

elif st.session_state.page == "Report":

    render_header(
        "Due Diligence Report",
        "Structured output based on the investigation and human review.",
    )

    if not job:

        st.markdown(
            """
            <div class="workspace-empty">

                <div class="workspace-empty-title">
                    No report available yet
                </div>

                <div class="workspace-empty-text">
                    Complete an investigation before generating
                    the diligence report.
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

    else:

        counts = service.review_counts(findings)

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Findings",
            counts["total"],
        )

        c2.metric(
            "Approved",
            counts["approved"],
        )

        c3.metric(
            "Pending review",
            counts["needs_review"],
        )

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown(
            """
            <div class="dd-card">

                <div class="dd-card-title">
                    Executive summary
                </div>

                <div class="dd-card-text">
                    This report summarizes the findings produced
                    during the due diligence investigation. Findings
                    remain subject to human review and are linked to
                    supporting source evidence.
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

        approved = [
            f for f in findings
            if f.get("status") == "APPROVED"
        ]

        if approved:

            st.subheader(
                "Approved findings"
            )

            for finding in approved:

                st.markdown(
                    f"""
                    <div class="finding">

                        <div class="finding-title">
                            {finding.get(
                                "description",
                                "Finding"
                            )}
                        </div>

                        <div class="finding-meta">
                            {finding.get(
                                "workstream",
                                finding.get(
                                    "category",
                                    "General"
                                )
                            ).title()}
                        </div>

                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        else:

            st.info(
                "No findings have been approved yet."
            )


# ============================================================
# ACTIVITY
# ============================================================

elif st.session_state.page == "Activity":

    render_header(
        "Activity",
        "A chronological record of the due diligence workflow.",
    )

    activity = service.activity_feed(
        job,
        findings,
    )

    if not activity:

        st.markdown(
            """
            <div class="workspace-empty">

                <div class="workspace-empty-title">
                    No activity yet
                </div>

                <div class="workspace-empty-text">
                    Activity will appear here as documents are
                    processed, investigations run, and findings
                    are reviewed.
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

    else:

        st.markdown(
            '<div class="timeline">',
            unsafe_allow_html=True,
        )

        for item in activity:

            time_value = service.fmt_time(
                item.get("at", "")
            )

            st.markdown(
                f"""
                <div class="timeline-item">

                    <div class="timeline-dot"></div>

                    <div class="timeline-title">
                        {item.get("title", "Activity")}
                    </div>

                    <div class="timeline-detail">
                        {item.get("detail", "")}
                    </div>

                    <div class="timeline-detail">
                        {time_value}
                    </div>

                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown(
            "</div>",
            unsafe_allow_html=True,
        )