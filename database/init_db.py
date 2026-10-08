from database.session import Base, engine

# Register all models with the shared Base.

from retrieval.models.documents import (
    Document,
    DocumentChunk,
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


def init_db():

    Base.metadata.create_all(
        bind=engine
    )


if __name__ == "__main__":

    init_db()

    print(
        "Database tables initialized."
    )

from dd_requests.models import DDRequest
from tasks.models import DDTask
from reanalysis.models import DDReanalysisRun
