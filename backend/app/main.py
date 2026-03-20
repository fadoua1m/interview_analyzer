from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routes.job_description import router as jobs_router
from app.routes.interview       import router as interviews_router
from app.routes.analysis        import router as analysis_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.analysis_pipeline.text.helpers import load_embedder, load_nli
    print("[Startup] Loading MiniLM embedder...")
    load_embedder()
    print("[Startup] Loading DeBERTa NLI...")
    load_nli()
    print("[Startup] Models ready")
    yield


app = FastAPI(title="AI Analyzer API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs_router,       prefix="/api/v1")
app.include_router(interviews_router, prefix="/api/v1")
app.include_router(analysis_router,   prefix="/api/v1")