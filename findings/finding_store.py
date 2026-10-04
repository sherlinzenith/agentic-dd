import contextvars
import json
from pathlib import Path
from datetime import datetime, timezone


RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
FINDINGS_FILE = RESULTS_DIR / "findings.json"
METRICS_FILE = RESULTS_DIR / "metrics.json"


# ---------------------------------------------------------------
# Job scope
# ---------------------------------------------------------------

_JOB = contextvars.ContextVar("dd_job", default=None)


def set_job(job_id):
    """Scope all store calls to one DD job."""
    _JOB.set(job_id or None)


def current_job():
    return _JOB.get()


def _files():
    job = _JOB.get()

    if not job:
        return FINDINGS_FILE, METRICS_FILE

    folder = RESULTS_DIR / "jobs" / job

    return (
        folder / "findings.json",
        folder / "metrics.json",
    )


def _ensure_results_dir():
    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    _files()[0].parent.mkdir(
        parents=True,
        exist_ok=True,
    )


# ---------------------------------------------------------------
# Finding identity
# ---------------------------------------------------------------

def _key(finding):
    """
    Stable identity used when an analysis is re-run.

    Workstream is included so that a Financial finding and a Legal
    finding with similar wording are never accidentally merged.
    """

    return (
        finding.get("workstream"),
        finding.get("category"),
        finding.get("description"),
    )


# ---------------------------------------------------------------
# Findings
# ---------------------------------------------------------------

def save_findings(findings):
    """
    Save findings while preserving existing human review decisions
    for the same finding when an analysis is re-run.
    """

    _ensure_results_dir()

    old_findings = {
        _key(finding): finding
        for finding in load_findings()
    }

    for finding in findings:

        previous = old_findings.get(
            _key(finding)
        )

        if not previous:
            continue

        previous_review = previous.get(
            "human_review"
        )

        if previous_review and not finding.get(
            "human_review"
        ):
            finding["human_review"] = previous_review

            finding["status"] = previous.get(
                "status",
                finding.get("status"),
            )

        previous_history = previous.get(
            "review_history",
            [],
        )

        if previous_history and not finding.get(
            "review_history"
        ):
            finding["review_history"] = previous_history

    _files()[0].write_text(
        json.dumps(
            findings,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def load_findings():
    _ensure_results_dir()

    findings_file = _files()[0]

    if not findings_file.exists():
        return []

    try:
        return json.loads(
            findings_file.read_text(
                encoding="utf-8"
            )
        )

    except json.JSONDecodeError:
        return []


# ---------------------------------------------------------------
# Human review
# ---------------------------------------------------------------

ALLOWED_REVIEW_ACTIONS = {
    "APPROVE",
    "REJECT",
    "REQUEST_MORE_EVIDENCE",
}


def save_review(
    finding_id,
    action,
    reviewer="",
    comment="",
):
    """
    Apply an explicit human review decision.

    APPROVE:
        Finding becomes APPROVED.

    REJECT:
        Finding becomes REJECTED.

    REQUEST_MORE_EVIDENCE:
        Finding becomes MORE_EVIDENCE_REQUIRED.

    Every review stores:
        reviewer
        action
        comment
        timestamp

    Previous review decisions are preserved in review_history.
    """

    action = (action or "").strip().upper()
    reviewer = (reviewer or "").strip()
    comment = (comment or "").strip()

    if action not in ALLOWED_REVIEW_ACTIONS:
        raise ValueError(
            "Invalid review action. "
            "Use APPROVE, REJECT, or REQUEST_MORE_EVIDENCE."
        )

    if not reviewer:
        raise ValueError(
            "Reviewer name is required."
        )

    if action in {
        "REJECT",
        "REQUEST_MORE_EVIDENCE",
    } and not comment:
        raise ValueError(
            "A comment is required for rejection "
            "or additional evidence requests."
        )

    findings = load_findings()

    for finding in findings:

        if finding.get("finding_id") != finding_id:
            continue

        current_status = finding.get(
            "status"
        )

        if current_status not in {
            "REVIEW_REQUIRED",
            "MORE_EVIDENCE_REQUIRED",
        }:
            raise ValueError(
                f"Finding {finding_id} is already "
                f"{current_status} and cannot be reviewed again."
            )

        if action == "APPROVE":
            status = "APPROVED"

        elif action == "REJECT":
            status = "REJECTED"

        else:
            status = "MORE_EVIDENCE_REQUIRED"

        old_review = finding.get(
            "human_review"
        )

        if old_review:
            history = finding.setdefault(
                "review_history",
                [],
            )

            history.append(old_review)

        review = {
            "action": action,
            "reviewer": reviewer,
            "comment": comment,
            "reviewed_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }

        finding["status"] = status
        finding["human_review"] = review

        save_findings(findings)

        return finding

    raise ValueError(
        f"Finding {finding_id} not found."
    )


# ---------------------------------------------------------------
# More evidence workflow
# ---------------------------------------------------------------

def reopen_more_evidence():
    """
    Move findings waiting for more evidence back into the
    human-review queue.

    The previous REQUEST_MORE_EVIDENCE decision remains in
    review_history.
    """

    findings = load_findings()

    for finding in findings:

        if finding.get("status") != (
            "MORE_EVIDENCE_REQUIRED"
        ):
            continue

        history = finding.setdefault(
            "review_history",
            [],
        )

        current_review = finding.get(
            "human_review"
        )

        if current_review:
            history.append(
                current_review
            )

        finding["human_review"] = None
        finding["status"] = "REVIEW_REQUIRED"

    _ensure_results_dir()

    _files()[0].write_text(
        json.dumps(
            findings,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


# ---------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------

def save_metrics(metrics):
    _ensure_results_dir()

    _files()[1].write_text(
        json.dumps(
            metrics,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def load_metrics():
    metrics_file = _files()[1]

    if not metrics_file.exists():
        return []

    try:
        return json.loads(
            metrics_file.read_text(
                encoding="utf-8"
            )
        )

    except json.JSONDecodeError:
        return []


# ---------------------------------------------------------------
# Reset
# ---------------------------------------------------------------

def reset_findings():
    """
    Start a new DD job by clearing findings and metrics
    for the current job.
    """

    _ensure_results_dir()

    findings_file, metrics_file = _files()

    findings_file.write_text(
        "[]",
        encoding="utf-8",
    )

    metrics_file.write_text(
        "[]",
        encoding="utf-8",
    )       