"""SecureVDR - Due Diligence workspace.

Documents -> organized by workstream -> scope -> plan -> investigation
-> human review (with source evidence) -> report.
"""

import json

import streamlit as st

from ui import service as svc
from ui.theme import (
    apply_theme,
    badge,
    brand,
    card,
    esc,
    header,
    metric,
    stepper,
)


WORKSPACE_NAME = "AsterNova Technologies"


NAV = [
    "Overview",
    "Documents",
    "Due Diligence",
    "Review",
    "Report",
    "Activity",
]


CATEGORY_LABEL = {
    "financial": "Financial",
    "legal": "Legal",
    "other": "Other",
}


TYPE_LABEL = {
    "income_statement": "Income statement",
    "balance_sheet": "Balance sheet",
    "cash_flow": "Cash flow statement",
    "revenue_report": "Revenue report",
    "contract": "Contract / agreement",
    "unclassified": "Unclassified",
}


SEV_KIND = {
    "HIGH": "b-bad",
    "MEDIUM": "b-warn",
    "LOW": "",
}


STATUS_LABEL = {
    "REVIEW_REQUIRED": (
        "Needs review",
        "b-warn",
    ),
    "APPROVED": (
        "Approved",
        "b-ok",
    ),
    "REJECTED": (
        "Rejected",
        "b-bad",
    ),
    "MORE_EVIDENCE_REQUIRED": (
        "More evidence requested",
        "b-brand",
    ),
}


VERIFY_LABEL = {
    "VERIFIED": (
        "Evidence verified",
        "b-ok",
    ),
    "PARTIAL": (
        "Partly verified",
        "b-warn",
    ),
    "UNVERIFIED": (
        "Evidence not found in source",
        "b-bad",
    ),
    "NO_EVIDENCE": (
        "Missing information",
        "",
    ),
}


CHECKS = {
    "financial": [
        "Income statement arithmetic (gross profit to profit after tax)",
        "Revenue: quarterly figures vs reported total, and income statement vs revenue report",
        "Balance sheet: asset and liability lines vs totals",
        "Cash flow: sections vs net change, closing cash vs balance sheet",
        "Net income vs profit after tax across documents",
        "Key metrics: margins, debt, interest cover, free cash flow",
    ],
    "legal": [
        "Identify contracts and agreements",
        "Change of control and assignment restrictions",
        "Termination for convenience and auto-renewal",
        "Exclusivity, non-compete and uncapped liability",
        "Missing standard clauses (governing law, limitation of liability)",
    ],
}


# ===============================================================
# CONFIG
# ===============================================================

st.set_page_config(
    page_title="SecureVDR | Due Diligence",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme()


# ===============================================================
# SESSION STATE
# ===============================================================

if "_goto" in st.session_state:
    st.session_state.nav = st.session_state.pop("_goto")

st.session_state.setdefault("nav", "Overview")
st.session_state.setdefault("reviewer", "")
st.session_state.setdefault("upl", 0)
st.session_state.setdefault("sel", None)
st.session_state.setdefault("active_job_id", None)
st.session_state.setdefault("qa_service", None)
st.session_state.setdefault("qa_signature", None)
st.session_state.setdefault("qa_result", None)
st.session_state.setdefault("qa_question", "")


def goto(page):
    st.session_state["_goto"] = page
    st.rerun()


# ===============================================================
# WORKSPACE
# ===============================================================

@st.cache_data(show_spinner=False)
def _workspace(file_sig, override_sig):
    return svc.organized_workspace()


current_files = svc.list_files()

workspace_file_signature = tuple(
    (
        f.name,
        f.stat().st_mtime_ns,
        f.stat().st_size,
    )
    for f in current_files
)

override_signature = json.dumps(
    svc.load_overrides(),
    sort_keys=True,
)

docs, rows, summary, unreadable = _workspace(
    workspace_file_signature,
    override_signature,
)


# ===============================================================
# ACTIVE JOB
# ===============================================================

def get_active_job():
    active_job_id = st.session_state.get("active_job_id")

    if not active_job_id:
        return None

    latest = svc.latest_job()

    if not latest:
        return None

    if latest.get("job_id") != active_job_id:
        return None

    return latest


job = get_active_job()

job_id = job["job_id"] if job else None

findings = (
    svc.findings_for(job_id)
    if job_id
    else []
)

counts = svc.review_counts(findings)

status = (
    job["status"]
    if job
    else None
)


# ===============================================================
# WORKSPACE CHANGE CHECK
# ===============================================================

def _job_has_current_documents(
    current_rows,
    current_job,
):
    if not current_job:
        return False

    job_docs = (
        current_job.get("documents")
        or current_job.get("document_snapshot")
        or current_job.get("workspace_documents")
    )

    if not job_docs:
        return True

    current_names = {
        r.get("document")
        for r in current_rows
        if r.get("document")
    }

    job_names = set()

    for document in job_docs:

        if isinstance(document, str):
            job_names.add(document)

        elif isinstance(document, dict):

            name = (
                document.get("document")
                or document.get("name")
                or document.get("file_name")
            )

            if name:
                job_names.add(name)

    if not job_names:
        return True

    return current_names == job_names


workspace_changed_since_job = False

if job:
    workspace_changed_since_job = not _job_has_current_documents(
        rows,
        job,
    )


# ===============================================================
# SIDEBAR
# ===============================================================

brand()

st.sidebar.markdown(
    f"""
    <div class="wsbox">
        <small>Workspace</small>
        <b>{esc(WORKSPACE_NAME)}</b>
    </div>
    """,
    unsafe_allow_html=True,
)

st.sidebar.radio(
    "Navigation",
    NAV,
    key="nav",
    label_visibility="collapsed",
)

st.sidebar.markdown(
    "<div style='height:24px'></div>",
    unsafe_allow_html=True,
)

st.sidebar.text_input(
    "Signed in as",
    key="reviewer",
    help="Recorded on every review decision.",
)

page = st.session_state.nav


# ===============================================================
# PROGRESS
# ===============================================================

def progress_steps():

    has_docs = bool(rows)
    ran = job is not None

    reviewed = (
        ran
        and counts["total"] > 0
        and counts["needs_review"] == 0
        and counts["more_evidence"] == 0
    )

    done = status == "REVIEW_COMPLETE"

    flags = [
        has_docs,
        has_docs,
        ran,
        ran,
        reviewed
        or (
            ran
            and counts["total"] == 0
            and done
        ),
        done,
    ]

    labels = [
        "Upload",
        "Organize",
        "Scope & plan",
        "Investigation",
        "Human review",
        "Report",
    ]

    output = []
    found_now = False

    for label, complete in zip(labels, flags):

        if complete:
            output.append((label, "done"))

        elif not found_now:
            output.append((label, "now"))
            found_now = True

        else:
            output.append((label, "todo"))

    return output


# ===============================================================
# OVERVIEW
# ===============================================================

def page_overview():

    header(
        "Workspace",
        "Overview",
        f"{WORKSPACE_NAME} · due diligence progress and what needs attention next.",
    )

    stepper(progress_steps())

    c = st.columns(5)

    metric(
        c[0],
        "Documents",
        summary["total"],
        f"{summary['financial']} financial · {summary['legal']} legal",
    )

    metric(
        c[1],
        "Findings",
        counts["total"],
        (
            "from the current investigation"
            if job
            else "no investigation yet"
        ),
    )

    metric(
        c[2],
        "Needs review",
        counts["needs_review"],
    )

    metric(
        c[3],
        "Approved",
        counts["approved"],
    )

    metric(
        c[4],
        "Rejected",
        counts["rejected"],
    )

    st.markdown(
        "<div style='height:14px'></div>",
        unsafe_allow_html=True,
    )

    left, right = st.columns([3, 2])

    with left:

        if not rows:

            card(
                "Start by uploading documents",
                "Add the deal documents to the workspace. They are organized into Financial and Legal workstreams automatically.",
            )

            if st.button(
                "Upload documents",
                type="primary",
            ):
                goto("Documents")

        elif not job:

            card(
                "Documents are ready",
                f"{summary['financial']} financial and {summary['legal']} legal documents are organized. Choose what to investigate.",
            )

            if st.button(
                "Set up due diligence",
                type="primary",
            ):
                goto("Due Diligence")

        elif workspace_changed_since_job:

            card(
                "New documents are available",
                "The workspace contains documents that were not part of the current investigation.",
            )

            if st.button(
                "Run investigation with current documents",
                type="primary",
            ):
                goto("Due Diligence")

        elif (
            counts["more_evidence"]
            and not counts["needs_review"]
        ):

            card(
                "Waiting for additional evidence",
                "A reviewer requested more evidence. Upload the documents, then re-run the analysis.",
            )

            if st.button("Add documents"):
                goto("Documents")

        elif counts["needs_review"]:

            card(
                f"{counts['needs_review']} finding(s) need your review",
                "Check the source evidence for each item before approving or rejecting.",
            )

            if st.button(
                "Open review queue",
                type="primary",
            ):
                goto("Review")

        elif status == "REVIEW_COMPLETE":

            card(
                "Review complete",
                "All findings have a reviewer decision. The report contains approved findings only.",
            )

            if st.button(
                "Open report",
                type="primary",
            ):
                goto("Report")

        else:

            card(
                "Finish the review",
                "Every finding has a decision. Complete the review to unlock the report.",
            )

            if st.button(
                "Go to review",
                type="primary",
            ):
                goto("Review")

    with right:

        missing = svc.readiness_for(
            rows,
            [
                "financial",
                "legal",
            ],
        )

        st.markdown("### Document readiness")

        st.caption(
            "What a diligence review normally expects to find."
        )

        for ws, readiness_info in missing.items():

            if (
                not summary[ws]
                and not readiness_info["missing"]
            ):
                continue

            c1, c2 = st.columns([3, 1])

            with c1:
                st.markdown(
                    f"**{CATEGORY_LABEL[ws]}**"
                )

            with c2:

                if readiness_info["missing"]:
                    st.warning(
                        f"{len(readiness_info['missing'])} missing"
                    )
                else:
                    st.success("Complete")

            if readiness_info["missing"]:

                st.caption(
                    "Missing: "
                    + ", ".join(
                        readiness_info["missing"]
                    )
                )


# ===============================================================
# DOCUMENTS
# ===============================================================

def _on_category(name):

    svc.set_category(
        name,
        st.session_state[
            f"cat_{name}"
        ].lower(),
    )


def page_documents():

    header(
        "Workspace",
        "Documents",
        "Upload everything together. Documents are sorted into the workstream that will review them; you can correct any placement.",
    )

    for msg in st.session_state.pop(
        "upload_msgs",
        [],
    ):

        if msg["ok"]:

            st.success(
                f"{msg['document']}: added ({msg['pages']} page(s))"
            )

        else:

            st.error(
                f"{msg['document']}: could not be read — {msg['error']}"
            )

    files = st.file_uploader(
        "Upload documents",
        type=svc.UPLOAD_TYPES,
        accept_multiple_files=True,
        key=f"uploader_{st.session_state.upl}",
        label_visibility="collapsed",
    )

    if files and st.button(
        f"Add {len(files)} document(s) to workspace",
        type="primary",
    ):

        st.session_state.upload_msgs = (
            svc.save_uploads(files)
        )

        st.session_state.upl += 1

        st.cache_data.clear()

        st.rerun()

    for u in unreadable:

        st.warning(
            f"{u['document']} could not be read: {u['error']}"
        )

    if not rows:

        card(
            "No documents yet",
            "Upload PDF or text documents to begin.",
        )

        return

    c = st.columns(4)

    metric(
        c[0],
        "Documents",
        summary["total"],
    )

    metric(
        c[1],
        "Financial",
        summary["financial"],
    )

    metric(
        c[2],
        "Legal",
        summary["legal"],
    )

    metric(
        c[3],
        "Other",
        summary["other"],
        "not used in a review",
    )

    st.markdown(
        "<div style='height:10px'></div>",
        unsafe_allow_html=True,
    )

    tabs = st.tabs(
        [
            f"Financial ({summary['financial']})",
            f"Legal ({summary['legal']})",
            f"Other ({summary['other']})",
        ]
    )

    for tab, category in zip(
        tabs,
        [
            "financial",
            "legal",
            "other",
        ],
    ):

        with tab:

            group = [
                r
                for r in rows
                if r["category"] == category
            ]

            if not group:
                st.caption(
                    "No documents in this workstream."
                )

            for r in group:

                a, b, c2, d = st.columns(
                    [5, 2, 2, 1]
                )

                confidence = (
                    f"{int(r['confidence'] * 100)}% match"
                    if r["confidence"]
                    else "no match"
                )

                a.markdown(
                    f"""
                    <div class="doc-name">
                        {esc(r["document"])}
                    </div>
                    <div class="doc-meta">
                        {esc(
                            TYPE_LABEL.get(
                                r["type"],
                                r["type"],
                            )
                        )}
                        · {r["pages"]} page(s)
                        · {esc(r["reason"])}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                b.markdown(
                    badge(
                        confidence,
                        (
                            "b-brand"
                            if r["confidence"] >= 0.5
                            else ""
                        ),
                    )
                    + (
                        badge(
                            "Set by reviewer",
                            "b-warn",
                        )
                        if r["manual"]
                        else ""
                    ),
                    unsafe_allow_html=True,
                )

                c2.selectbox(
                    "Workstream",
                    list(
                        CATEGORY_LABEL.values()
                    ),
                    index=list(
                        CATEGORY_LABEL
                    ).index(
                        r["category"]
                    ),
                    key=f"cat_{r['document']}",
                    on_change=_on_category,
                    args=(r["document"],),
                    label_visibility="collapsed",
                )

                if d.button(
                    "Remove",
                    key=f"rm_{r['document']}",
                ):

                    svc.remove_document(
                        r["document"]
                    )

                    st.cache_data.clear()

                    st.rerun()


# ===============================================================
# AI DD Q&A
# ===============================================================

def get_qa_service():
    """Build/reuse the AI DD Q&A service for the current workspace."""

    from qa.qa_service import DDQAService

    if st.session_state.get("qa_signature") != workspace_file_signature:
        st.session_state.qa_service = None
        st.session_state.qa_signature = workspace_file_signature
        st.session_state.qa_result = None

    if st.session_state.get("qa_service") is None:
        if not docs:
            return None

        qa = DDQAService()

        with st.spinner("Preparing workspace documents for AI Q&A…"):
            qa.build_index(docs)

        st.session_state.qa_service = qa

    return st.session_state.qa_service


def clear_ai_dd_qa():
    """Clear the Q&A input and previous answer safely before the next rerun."""
    st.session_state.qa_question = ""
    st.session_state.qa_result = None


def render_ai_dd_qa():
    """Render the user-facing AI DD Q&A without changing the existing DD UI."""

    st.markdown("---")
    st.markdown("### AI DD Q&A")
    st.caption(
        "Ask questions about the documents in this workspace. "
        "Answers are grounded in the available document evidence."
    )

    st.text_area(
        "Ask a question",
        key="qa_question",
        placeholder="For example: What documents do we have?",
        label_visibility="collapsed",
    )

    ask_col, clear_col = st.columns([1, 5])

    with ask_col:
        ask = st.button(
            "Ask AI",
            type="primary",
            use_container_width=True,
            key="ask_ai_dd_qa",
        )

    with clear_col:
        st.button(
            "Clear",
            key="clear_ai_dd_qa",
            on_click=clear_ai_dd_qa,
        )

    if ask:
        question = str(
            st.session_state.get("qa_question", "")
        ).strip()

        if not question:
            st.warning("Enter a question first.")
        else:
            try:
                qa = get_qa_service()

                if qa is None:
                    st.warning(
                        "There are no readable documents available for Q&A."
                    )
                else:
                    with st.spinner(
                        "Searching the workspace and generating an answer…"
                    ):
                        result = qa.answer(question)

                    st.session_state.qa_result = result

            except Exception as error:
                st.session_state.qa_result = None
                st.error(
                    f"AI Q&A could not answer the question: {error}"
                )

    result = st.session_state.get("qa_result")

    if not result:
        return

    st.markdown("#### Answer")
    st.write(result.answer)

    sources = result.sources or []

    if sources:
        st.markdown("#### Sources")

        for source in sources:
            document_name = source.document
            page_number = source.page

            st.markdown(
                f"**{document_name}** · page **{page_number}**"
            )

            with st.expander("View evidence"):
                st.write(source.text)


# ===============================================================
# DUE DILIGENCE
# ===============================================================

def page_dd():

    header(
        "Due Diligence",
        "Set up the investigation",
        "Choose the workstreams, check the plan, then start. Each workstream reviews only its own documents.",
    )

    if not rows:

        card(
            "No documents to review",
            "Upload documents first.",
        )

        if st.button(
            "Go to documents",
            type="primary",
        ):
            goto("Documents")

        return

    if workspace_changed_since_job:

        st.warning(
            "The workspace has changed since the current investigation. "
            "Starting a new investigation will use the current documents."
        )

    readiness = svc.readiness_for(
        rows,
        [
            "financial",
            "legal",
        ],
    )

    selected = []

    cols = st.columns(2)

    for col, ws, description in zip(
        cols,
        [
            "financial",
            "legal",
        ],
        [
            "Statement consistency, revenue reconciliation, cash flow and key metrics.",
            "Contract clauses that matter in a transaction, with the exact wording and page.",
        ],
    ):

        n = summary[ws]

        with col:

            st.markdown(
                f"""
                <div class="card">
                    <div class="card-h">
                        {CATEGORY_LABEL[ws]} due diligence
                    </div>
                    <div class="card-p">
                        {esc(description)}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown(
                badge(
                    f"{n} document(s)",
                    "b-brand" if n else "",
                ),
                unsafe_allow_html=True,
            )

            include = st.checkbox(
                f"Include {CATEGORY_LABEL[ws].lower()}",
                value=n > 0,
                disabled=n == 0,
                key=f"scope_{ws}",
            )

            if n == 0:

                st.caption(
                    "No documents in this workstream. "
                    "Upload or re-categorise documents first."
                )

            elif readiness[ws]["missing"]:

                st.caption(
                    "Not found in the workspace: "
                    + ", ".join(
                        readiness[ws]["missing"]
                    )
                )

            if include and n:
                selected.append(ws)

    if selected:

        st.markdown("### Investigation plan")

        for ws in selected:

            used_documents = [
                r["document"]
                for r in rows
                if r["category"] == ws
            ]

            st.markdown(
                f"**{CATEGORY_LABEL[ws]}**"
            )

            st.markdown(
                "**Documents used:** "
                + ", ".join(
                    used_documents
                )
            )

            st.markdown("**Checks:**")

            for check in CHECKS[ws]:
                st.markdown(
                    f"- {check}"
                )

        st.caption(
            "Every finding is verified against its source page. "
            + (
                "Findings that connect both workstreams are flagged for joint review. "
                if len(selected) == 2
                else ""
            )
            + "Nothing is concluded automatically; a reviewer approves each finding."
        )

        confirmed = st.checkbox(
            "I confirm this scope and the documents listed above."
        )

        if st.button(
            "Start investigation",
            type="primary",
            disabled=not confirmed,
        ):

            with st.status(
                "Running investigation…",
                expanded=True,
            ) as box:

                st.write(
                    "Reading the current workspace documents and applying "
                    "the selected plan."
                )

                try:

                    info = svc.run_investigation(
                        selected
                    )

                    new_job = svc.latest_job()

                    if not new_job:
                        raise RuntimeError(
                            "The investigation finished but no new DD job was found."
                        )

                    st.session_state.active_job_id = (
                        new_job["job_id"]
                    )

                    st.session_state.sel = None

                    st.session_state.flash = info

                    box.update(
                        label=(
                            "Investigation complete — "
                            "findings are ready for review"
                        ),
                        state="complete",
                    )

                except Exception as error:

                    box.update(
                        label="The investigation could not finish",
                        state="error",
                    )

                    st.error(
                        str(error)
                    )

                    return

            st.cache_data.clear()
            st.rerun()

    else:

        st.info(
            "Select at least one workstream with documents."
        )

    if job:

        st.markdown(
            "### Current investigation"
        )

        current_status_label = {
            "AWAITING_REVIEW": "Awaiting review",
            "AWAITING_EVIDENCE": "Awaiting evidence",
            "REVIEW_COMPLETE": "Review complete",
        }.get(
            status,
            status,
        )

        st.markdown(
            badge(
                current_status_label,
                "b-brand",
            ),
            unsafe_allow_html=True,
        )

        for item in svc.activity_feed(
            job,
            [],
        )[::-1]:

            st.markdown(
                f"""
                <div class="tl">
                    <span class="tl-dot"></span>
                    <div>
                        <div class="tl-t">
                            {esc(item["title"])}
                        </div>
                        <div class="tl-d">
                            {esc(item["detail"])}
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        if workspace_changed_since_job:

            st.warning(
                "New or changed documents are available. "
                "Start a new investigation to analyze the current workspace."
            )

        elif status == "AWAITING_EVIDENCE":

            st.warning(
                "A reviewer requested more evidence. "
                "Add the documents, then re-run the analysis."
            )

            if st.button(
                "Re-run analysis with current documents",
                type="primary",
            ):

                svc.resume(job_id)

                st.cache_data.clear()

                st.rerun()

        elif counts["needs_review"]:

            if st.button(
                f"Review {counts['needs_review']} finding(s)",
                type="primary",
            ):
                goto("Review")


    # -----------------------------------------------------------
    # AI DD Q&A
    # -----------------------------------------------------------
    render_ai_dd_qa()


# ===============================================================
# REVIEW
# ===============================================================

def _queue_label(finding):

    mark = {
        "APPROVED": "✓",
        "REJECTED": "✕",
        "MORE_EVIDENCE_REQUIRED": "…",
    }.get(
        finding["status"],
        "●",
    )

    return (
        f"{mark}  "
        f"{finding['finding_id']} · "
        f"{finding.get('category')}"
    )


def page_review():

    header(
        "Due Diligence",
        "Review findings",
        "Check the source evidence, then decide. Approving means a person has verified the finding — not that the AI is right.",
    )

    if not job:

        card(
            "Nothing to review yet",
            "Start an investigation first.",
        )

        if st.button(
            "Set up due diligence",
            type="primary",
        ):
            goto("Due Diligence")

        return

    if not findings:

        card(
            "No findings",
            "The investigation did not raise any items.",
        )

        return

    done = (
        counts["total"]
        - counts["needs_review"]
    )

    st.progress(
        done / counts["total"],
        text=(
            f"{done} of {counts['total']} decided · "
            f"{counts['approved']} approved · "
            f"{counts['rejected']} rejected · "
            f"{counts['more_evidence']} awaiting evidence"
        ),
    )

    f1, f2 = st.columns(2)

    workstream_pick = f1.selectbox(
        "Workstream",
        [
            "All",
            "Financial",
            "Legal",
            "Cross-workstream",
        ],
    )

    status_pick = f2.selectbox(
        "Status",
        [
            "Needs review",
            "All",
            "Approved",
            "Rejected",
            "More evidence requested",
        ],
    )

    workstream_key = {
        "Financial": "financial",
        "Legal": "legal",
        "Cross-workstream": "cross_domain",
    }.get(
        workstream_pick
    )

    status_key = {
        "Needs review": "REVIEW_REQUIRED",
        "Approved": "APPROVED",
        "Rejected": "REJECTED",
        "More evidence requested": "MORE_EVIDENCE_REQUIRED",
    }.get(
        status_pick
    )

    shown = [
        finding
        for finding in findings
        if (
            not workstream_key
            or finding.get("workstream")
            == workstream_key
        )
        and (
            not status_key
            or finding["status"]
            == status_key
        )
    ]

    qcol, dcol = st.columns([2, 5])

    with qcol:

        st.markdown(
            "**Review queue**"
        )

        if not shown:
            st.caption(
                "No findings match."
            )

        for finding in shown:

            if st.button(
                _queue_label(finding),
                key=f"q_{finding['finding_id']}",
                use_container_width=True,
                type=(
                    "primary"
                    if finding["finding_id"]
                    == st.session_state.sel
                    else "secondary"
                ),
            ):

                st.session_state.sel = (
                    finding["finding_id"]
                )

                st.rerun()

    current = next(
        (
            finding
            for finding in shown
            if finding["finding_id"]
            == st.session_state.sel
        ),
        shown[0]
        if shown
        else None,
    )

    with dcol:

        if current:
            render_finding(current)

    st.markdown("---")

    if counts["needs_review"]:

        st.caption(
            f"{counts['needs_review']} finding(s) still need a decision before the review can be completed."
        )

    elif status == "REVIEW_COMPLETE":

        st.success(
            "Review complete."
        )

        if st.button(
            "Open report",
            type="primary",
        ):
            goto("Report")

    else:

        if st.button(
            "Complete review",
            type="primary",
        ):

            svc.resume(job_id)

            st.cache_data.clear()

            st.rerun()


# ===============================================================
# REVIEW FINDING
# ===============================================================

def render_finding(finding):

    finding_id = finding["finding_id"]

    severity = finding.get(
        "severity",
        "-",
    )

    status_label, status_kind = STATUS_LABEL.get(
        finding["status"],
        (
            finding["status"],
            "",
        ),
    )

    verification = (
        finding.get(
            "evidence_verification"
        )
        or {}
    )

    verification_label, verification_kind = VERIFY_LABEL.get(
        verification.get("status"),
        (
            "",
            "",
        ),
    )

    reasoning = (
        finding.get(
            "ai_reasoning"
        )
        or {}
    )

    related = ", ".join(
        finding.get(
            "related_findings"
        )
        or []
    )


    # ===========================================================
    # FINDING HEADER
    # ===========================================================

    st.markdown(
        f"### {finding.get('category', 'Finding')}"
    )


    meta1, meta2, meta3 = st.columns(
        [2, 2, 3]
    )


    with meta1:

        st.markdown(
            f"**Finding ID**  \n"
            f"{finding_id}"
        )


    with meta2:

        workstream = (
            str(
                finding.get(
                    "workstream",
                    "",
                )
            )
            .replace(
                "_",
                " ",
            )
            .title()
        )

        st.markdown(
            f"**Workstream**  \n"
            f"{workstream}"
        )


    with meta3:

        st.markdown(
            "**Status**"
        )

        st.markdown(
            f"{status_label}  ·  "
            f"{severity}  ·  "
            f"{verification_label}"
        )


    st.divider()


    # ===========================================================
    # WHAT WAS FOUND
    # ===========================================================

    st.markdown(
        "#### What was found"
    )

    st.write(
        finding.get(
            "description",
            "",
        )
    )


    # ===========================================================
    # WHY IT MATTERS
    # ===========================================================

    st.markdown(
        "#### Why it matters"
    )

    st.write(
        reasoning.get(
            "why_it_matters"
        )
        or finding.get(
            "impact",
            "",
        )
    )


    # ===========================================================
    # WHAT TO CHECK
    # ===========================================================

    st.markdown(
        "#### What to check"
    )

    st.write(
        reasoning.get(
            "what_should_be_reviewed",
            "",
        )
    )


    if related:

        st.markdown(
            "#### Related findings"
        )

        st.write(
            related
        )


    # ===========================================================
    # SOURCE EVIDENCE
    # ===========================================================

    st.markdown(
        "#### Source evidence"
    )


    evidence = (
        finding.get(
            "evidence"
        )
        or []
    )


    if not evidence:

        st.info(
            "No document evidence: this item reports missing information."
        )


    for index, evidence_item in enumerate(
        evidence
    ):

        document_name = (
            evidence_item.get(
                "document"
            )
            or "Unknown document"
        )


        page_number = (
            evidence_item.get(
                "page",
                "-",
            )
        )


        field_name = (
            evidence_item.get(
                "field",
                "",
            )
        )


        evidence_value = (
            evidence_item.get(
                "value",
                "",
            )
        )


        with st.container(
            border=True
            if hasattr(
                st,
                "container",
            )
            else False
        ):

            st.markdown(
                f"**{document_name}** · page **{page_number}**"
            )


            if field_name:

                st.markdown(
                    f"**{field_name}**"
                )


            if evidence_value:

                st.info(
                    str(
                        evidence_value
                    )
                )


        with st.expander(
            "View source page"
        ):

            source_text = svc.page_text(
                docs,
                document_name,
                page_number,
            )


            if source_text:

                value = str(
                    evidence_value
                    or ""
                )


                if value:

                    source_lines = source_text.splitlines()

                    matched = False

                    for line in source_lines:

                        if value.lower() in line.lower():

                            st.markdown(
                                f"> **{line}**"
                            )

                            matched = True

                        else:

                            st.write(
                                line
                            )


                    if not matched:

                        st.text(
                            source_text
                        )

                else:

                    st.text(
                        source_text
                    )

            else:

                st.info(
                    "Page not available."
                )


    # ===========================================================
    # EVIDENCE VERIFICATION
    # ===========================================================

    issues = verification.get(
        "issues"
    ) or []


    if issues:

        st.error(
            "Evidence check: "
            + "; ".join(
                issues
            )
        )


    # ===========================================================
    # REVIEW HISTORY
    # ===========================================================

    history = (
        finding.get(
            "review_history"
        )
        or []
    ) + (
        [
            finding["human_review"]
        ]
        if finding.get(
            "human_review"
        )
        else []
    )


    if history:

        st.markdown(
            "#### Review history"
        )


        for review in history:

            reviewer_name = (
                review.get(
                    "reviewer"
                )
                or "Human reviewer"
            )


            action = (
                review.get(
                    "action",
                    "",
                )
                .replace(
                    "_",
                    " ",
                )
                .title()
            )


            review_time = svc.fmt_time(
                review.get(
                    "reviewed_at",
                    "",
                )
            )


            comment = review.get(
                "comment"
            )


            st.markdown(
                f"**{reviewer_name}** · "
                f"{action} · "
                f"{review_time}"
            )


            if comment:

                st.caption(
                    comment
                )


    # ===========================================================
    # HUMAN REVIEW
    # ===========================================================

    if finding["status"] != "REVIEW_REQUIRED":

        return


    st.divider()


    st.markdown(
        "#### Human review"
    )


    st.caption(
        "Review the evidence above, then choose one action."
    )


    comment = st.text_area(
        "Reviewer comment",
        key=f"cmt_{finding_id}",
        placeholder=(
            "Required to reject or request more evidence. "
            "Recommended when approving."
        ),
    )


    acknowledged = st.checkbox(
        "I have checked the source evidence for this finding.",
        key=f"ack_{finding_id}",
    )


    a, b, c = st.columns(3)


    def decide(action):

        reviewer = (
            st.session_state.reviewer.strip()
        )


        if not reviewer:

            st.error(
                "Enter the human reviewer name in "
                "'Signed in as' before making a decision."
            )

            return


        try:

            svc.review(
                job_id,
                finding_id,
                action,
                reviewer,
                comment.strip(),
            )

        except Exception as error:

            st.error(
                f"Could not save the review decision: {error}"
            )

            return


        st.session_state.sel = None

        st.cache_data.clear()

        st.rerun()


    with a:

        if st.button(
            "Approve finding",
            type="primary",
            disabled=not acknowledged,
            key=f"ap_{finding_id}",
            use_container_width=True,
        ):

            decide(
                "APPROVE"
            )


    with b:

        if st.button(
            "Reject",
            key=f"rj_{finding_id}",
            use_container_width=True,
        ):

            if comment.strip():

                decide(
                    "REJECT"
                )

            else:

                st.warning(
                    "Add a comment explaining the rejection."
                )


    with c:

        if st.button(
            "Request more evidence",
            key=f"me_{finding_id}",
            use_container_width=True,
        ):

            if comment.strip():

                decide(
                    "REQUEST_MORE_EVIDENCE"
                )

            else:

                st.warning(
                    "Say what additional evidence is needed."
                )


# ===============================================================
# REPORT
# ===============================================================

def page_report():

    header(
        "Due Diligence",
        "Report",
        "Approved findings are presented as conclusions. Rejected items are excluded and open items are listed separately.",
    )

    if (
        not job
        or counts["needs_review"]
        or (
            findings
            and status != "REVIEW_COMPLETE"
        )
    ):

        card(
            "Report not available yet",
            "Complete the human review first. The report is built only from decisions a reviewer has made.",
        )

        if st.button(
            "Go to review",
            type="primary",
        ):
            goto("Review")

        return


    html_doc = svc.build_report(
        WORKSPACE_NAME,
        findings,
        svc.metrics_for(job_id),
        rows,
        job.get(
            "readiness",
            {},
        ),
        job.get(
            "plan",
            [],
        ),
    )


    st.download_button(
        "Download report",
        html_doc,
        file_name="due_diligence_report.html",
        mime="text/html",
        type="primary",
    )


    if hasattr(
        st,
        "iframe",
    ):

        st.iframe(
            html_doc,
            height=900,
        )

    else:

        st.components.v1.html(
            html_doc,
            height=900,
            scrolling=True,
        )


# ===============================================================
# ACTIVITY
# ===============================================================

def page_activity():

    header(
        "Workspace",
        "Activity",
        "Everything the system did and every reviewer decision, newest first.",
    )

    feed = svc.activity_feed(
        job,
        findings,
    )

    if not feed:

        card(
            "No activity yet",
            "Activity appears here once an investigation has run.",
        )

        return


    # -----------------------------------------------------------
    # IMPORTANT:
    # Activity previously used raw HTML:
    #
    # <div class="tl">
    # <span class="tl-dot"></span>
    # <div class="tl-t">...</div>
    #
    # That HTML was appearing literally in the UI.
    #
    # Use native Streamlit components instead.
    # -----------------------------------------------------------

    for item in feed:

        title = str(
            item.get(
                "title",
                "",
            )
        )

        detail = str(
            item.get(
                "detail",
                "",
            )
        )

        timestamp = svc.fmt_time(
            item.get(
                "at",
                "",
            )
        )

        st.markdown(
            f"**{title}**"
        )

        if detail:

            st.write(
                detail
            )

        if timestamp:

            st.caption(
                timestamp
            )

        st.divider()


# ===============================================================
# ROUTER
# ===============================================================

{
    "Overview": page_overview,
    "Documents": page_documents,
    "Due Diligence": page_dd,
    "Review": page_review,
    "Report": page_report,
    "Activity": page_activity,
}[page]()