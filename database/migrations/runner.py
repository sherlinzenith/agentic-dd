"""
Database Migration Runner for Due Diligence Platform.
Tracks and applies versioned schema migrations against PostgreSQL with pgvector.
"""
from __future__ import annotations

import logging
from datetime import datetime
from sqlalchemy import text
from database.session import engine

logger = logging.getLogger(__name__)

MIGRATIONS = [
    {
        "version": "001_initial_schema",
        "description": "Initial tables for projects, workstreams, scopes, documents, findings, and evidence",
        "sql": """
        -- Pgvector extension
        CREATE EXTENSION IF NOT EXISTS vector;
        """,
    },
    {
        "version": "002_evidence_validation_metadata",
        "description": "Add validation reason, match method, and confidence columns to dd_evidence",
        "sql": """
        ALTER TABLE dd_evidence ADD COLUMN IF NOT EXISTS validation_reason TEXT;
        ALTER TABLE dd_evidence ADD COLUMN IF NOT EXISTS match_method VARCHAR(50);
        ALTER TABLE dd_evidence ADD COLUMN IF NOT EXISTS confidence FLOAT;
        """,
    },
    {
        "version": "003_tasks_and_reanalysis_indexes",
        "description": "Performance indexes for tasks and reanalysis runs",
        "sql": """
        CREATE INDEX IF NOT EXISTS idx_tasks_project_status ON dd_tasks (project_id, status);
        CREATE INDEX IF NOT EXISTS idx_reanalysis_status ON reanalysis_runs (status);
        CREATE INDEX IF NOT EXISTS idx_findings_project_workstream ON dd_findings (project_id, workstream);
        """,
    },
]


def ensure_migration_table():
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(100) PRIMARY KEY,
                description TEXT,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        conn.commit()


def get_applied_migrations() -> set[str]:
    ensure_migration_table()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version FROM schema_migrations"))
        return {row[0] for row in result.fetchall()}


def apply_migrations() -> list[str]:
    """Applies all pending migrations in order and returns the list of newly applied versions."""
    ensure_migration_table()
    applied = get_applied_migrations()
    newly_applied = []

    with engine.connect() as conn:
        for m in MIGRATIONS:
            v = m["version"]
            if v not in applied:
                logger.info("Applying migration %s: %s", v, m["description"])
                conn.execute(text(m["sql"]))
                conn.execute(
                    text("INSERT INTO schema_migrations (version, description, applied_at) VALUES (:v, :d, :t)"),
                    {"v": v, "d": m["description"], "t": datetime.utcnow()},
                )
                conn.commit()
                newly_applied.append(v)

    return newly_applied


if __name__ == "__main__":
    applied = apply_migrations()
    print(f"Applied {len(applied)} new migrations: {applied}")
