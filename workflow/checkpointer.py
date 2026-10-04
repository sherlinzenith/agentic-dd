"""Saves job state so a paused DD job survives a restart.

SQLite if 'langgraph-checkpoint-sqlite' is installed, otherwise in-memory (lost on restart).
    pip install langgraph-checkpoint-sqlite
"""

import sqlite3
from pathlib import Path

DB_FILE = Path(__file__).resolve().parent.parent / "results" / "dd_jobs.sqlite"


def get_checkpointer():

    try:
        from langgraph.checkpoint.sqlite import SqliteSaver

        DB_FILE.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(DB_FILE), check_same_thread=False)
        return SqliteSaver(conn)

    except ImportError:

        from langgraph.checkpoint.memory import MemorySaver

        print(
            "[Checkpointer] langgraph-checkpoint-sqlite not installed: "
            "using memory (jobs are lost on restart)."
        )
        return MemorySaver()
