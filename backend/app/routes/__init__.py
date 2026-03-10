# app/routes/__init__.py
from app.routes.job_description import router as jobs_router
from app.routes.ai import router as ai_router

__all__ = ["jobs_router", "ai_router"]