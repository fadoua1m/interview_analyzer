from fastapi import APIRouter, HTTPException
from app.supabase_client import supabase
from app.schemas.job_description import (
    JobDescriptionCreate,
    JobDescriptionUpdate,
    JobDescriptionResponse,
)

router = APIRouter(prefix="/jobs", tags=["Jobs"])

TABLE = "job_descriptions"


@router.post("", response_model=JobDescriptionResponse, status_code=201)
def create_job(payload: JobDescriptionCreate):
    payload.validate_level()
    result = (
        supabase.table(TABLE)
        .insert(payload.model_dump())
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create job")
    return result.data[0]


@router.get("", response_model=list[JobDescriptionResponse])
def list_jobs():
    result = (
        supabase.table(TABLE)
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )
    return result.data


@router.get("/{id}", response_model=JobDescriptionResponse)
def get_job(id: str):
    result = (
        supabase.table(TABLE)
        .select("*")
        .eq("id", id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Job not found")
    return result.data[0]


@router.patch("/{id}", response_model=JobDescriptionResponse)
def update_job(id: str, payload: JobDescriptionUpdate):
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Check exists
    existing = supabase.table(TABLE).select("id").eq("id", id).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Job not found")

    result = (
        supabase.table(TABLE)
        .update(data)
        .eq("id", id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to update job")
    return result.data[0]


@router.delete("/{id}", status_code=204)
def delete_job(id: str):
    existing = supabase.table(TABLE).select("id").eq("id", id).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Job not found")

    supabase.table(TABLE).delete().eq("id", id).execute()