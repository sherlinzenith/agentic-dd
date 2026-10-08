from fastapi import FastAPI

from api.v1.documents import router as documents_router
from api.v1.projects import router as projects_router
from api.v1.scopes import router as scopes_router
from api.v1.investigations import router as investigations_router
from api.v1.findings import router as findings_router


app = FastAPI(
    title="Agentic Due Diligence Platform",
    version="1.0.0",
)


app.include_router(
    documents_router
)

app.include_router(
    projects_router
)

app.include_router(
    scopes_router
)

app.include_router(
    investigations_router
)

app.include_router(
    findings_router
)


@app.get("/health")
def health():

    return {
        "status": "ok",
        "service": "agentic-due-diligence",
    }

from api.v1.requests import router as requests_router
from api.v1.tasks import router as tasks_router
from api.v1.reanalysis import router as reanalysis_router

app.include_router(requests_router)
app.include_router(tasks_router)
app.include_router(reanalysis_router)
