"""One line of the 'AI Activity' timeline shown in the UI."""

from datetime import datetime, timezone


def log(step, detail, status="done"):
    return {
        "step": step,
        "status": status,
        "detail": detail,
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
