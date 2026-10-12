from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.v1.documents import router as documents_router
from api.v1.projects import router as projects_router
from api.v1.scopes import router as scopes_router
from api.v1.investigations import router as investigations_router
from api.v1.findings import router as findings_router
from workers.reanalysis_worker import start_background_worker, stop_background_worker


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Automatically start background reanalysis worker thread on server startup
    start_background_worker(poll_interval=3.0)
    yield
    # Stop background worker thread gracefully on server shutdown
    stop_background_worker()


app = FastAPI(
    title="Agentic Due Diligence Platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "Agentic Due Diligence Platform API",
        "health": "/health",
        "docs": "/docs",
        "version": "1.0.0",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "agentic-due-diligence",
    }

from api.v1.requests import router as requests_router
from api.v1.tasks import router as tasks_router
from api.v1.reanalysis import router as reanalysis_router
from api.v1.orchestrator import router as orchestrator_router
from api.v1.chat import router as chat_router
from api.v1.reports import router as reports_router

app.include_router(requests_router)
app.include_router(tasks_router)
app.include_router(reanalysis_router)
app.include_router(orchestrator_router)
app.include_router(chat_router)
app.include_router(reports_router)
