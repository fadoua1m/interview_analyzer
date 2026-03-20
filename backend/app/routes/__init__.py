# app/routes/__init__.py
from app.routes.job_description import router as jobs_router
from app.routes.interview       import router as interviews_router

__all__ = ["jobs_router", "interviews_router"]