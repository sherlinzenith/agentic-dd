from database.session import Base, engine

# Register all models with the shared Base.

from retrieval.models.documents import (
    Document,
    DocumentChunk,
    DocumentTable,
)

from retrieval.models.projects import DDProject
from retrieval.models.workstreams import DDWorkstream
from retrieval.models.scopes import DDScope
from retrieval.models.investigations import DDInvestigation

from findings.models import (
    Finding,
    FindingReview,
)

from evidence.models import Evidence
from dd_requests.models import DDRequest
from tasks.models import DDTask
from reanalysis.models import DDReanalysisRun
from chatbot.models import DDConversation, DDConversationMessage


def init_db():
    Base.metadata.create_all(
        bind=engine
    )

    # Idempotent migration for new columns on dd_evidence in existing databases
    if engine.dialect.name == "postgresql":
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE dd_evidence ADD COLUMN IF NOT EXISTS validation_reason TEXT;"))
            conn.execute(text("ALTER TABLE dd_evidence ADD COLUMN IF NOT EXISTS match_method VARCHAR(50);"))
            conn.execute(text("ALTER TABLE dd_evidence ADD COLUMN IF NOT EXISTS confidence FLOAT;"))
            conn.commit()


if __name__ == "__main__":

    init_db()

    print(
        "Database tables initialized."
    )
