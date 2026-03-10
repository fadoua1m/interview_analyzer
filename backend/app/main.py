# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routes.job_description import router as jobs_router
from app.routes.ai import router as ai_router

app = FastAPI(title="AI Analyzer API", version="1.0.0")

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(jobs_router, prefix="/api/v1")
app.include_router(ai_router,   prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok", "env": settings.app_env}