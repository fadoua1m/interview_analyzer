# app/routes/ai.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.gemini_service import (
    enhance_description,
    generate_requirements,
    enhance_requirements,
)

router = APIRouter(prefix="/ai", tags=["AI"])


# ── Request / Response schemas ───────────────────────────────────────────────

class EnhanceDescriptionRequest(BaseModel):
    title:       str
    company:     str
    description: str

class GenerateRequirementsRequest(BaseModel):
    title:       str
    company:     str
    description: str

class EnhanceRequirementsRequest(BaseModel):
    title:        str
    requirements: str

class AITextResponse(BaseModel):
    result: str


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/enhance-description", response_model=AITextResponse)
def enhance_description_route(payload: EnhanceDescriptionRequest):
    if not payload.description.strip():
        raise HTTPException(400, "Description cannot be empty")
    try:
        return {"result": enhance_description(
            payload.title, payload.company, payload.description
        )}
    except Exception as e:
        raise HTTPException(500, f"Gemini error: {e}")


@router.post("/generate-requirements", response_model=AITextResponse)
def generate_requirements_route(payload: GenerateRequirementsRequest):
    if not payload.description.strip():
        raise HTTPException(400, "Description is required to generate requirements")
    try:
        return {"result": generate_requirements(
            payload.title, payload.company, payload.description
        )}
    except Exception as e:
        raise HTTPException(500, f"Gemini error: {e}")


@router.post("/enhance-requirements", response_model=AITextResponse)
def enhance_requirements_route(payload: EnhanceRequirementsRequest):
    if not payload.requirements.strip():
        raise HTTPException(400, "Requirements cannot be empty")
    try:
        return {"result": enhance_requirements(
            payload.title, payload.requirements
        )}
    except Exception as e:
        raise HTTPException(500, f"Gemini error: {e}")