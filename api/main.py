"""
Canonical API entry point exposing the Agentic Due Diligence FastAPI application.
Re-exports the fully configured app from app.new_main containing all routers
and the background reanalysis worker lifespan.
"""
from app.new_main import app

__all__ = ["app"]
