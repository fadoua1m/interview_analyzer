import traceback
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from app.supabase_client import supabase
from app.schemas.analysis import AnalysisRequest, QuestionInput, CandidateReport
from app.analysis_pipeline.pipeline import run_analysis

router = APIRouter(prefix="/analysis", tags=["Analysis"])


@router.post("/run", response_model=CandidateReport)
def run_analysis_route(payload: AnalysisRequest):
    existing = (
        supabase.table("interviews")
        .select("id")
        .eq("id", payload.interview_id)
        .execute()
    )
    if not existing.data:
        raise HTTPException(404, "Interview not found")

    try:
        report = run_analysis(payload)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"Analysis failed: {str(e)}")

    try:
        supabase.table("analysis_results").insert({
            "interview_id":  report.interview_id,
            "overall_score": report.overall_score,
            "relevance":     report.relevance.model_dump(),
            "soft_skills":   report.soft_skills.model_dump(),
            "generated_at":  report.generated_at.isoformat(),
        }).execute()
    except Exception:
        traceback.print_exc()

    return report


@router.post("/run-upload", response_model=CandidateReport)
def run_analysis_upload(
    video:        UploadFile = File(...),
    interview_id: str        = Form(...),
):
    """
    Upload a video file directly for testing.
    interview_id must be a valid UUID from your interviews table.
    Questions are fetched automatically from the database.
    """
    # fetch interview + questions from DB
    interview_row = (
        supabase.table("interviews")
        .select("id")
        .eq("id", interview_id)
        .execute()
    )
    if not interview_row.data:
        raise HTTPException(404, "Interview not found")

    questions_row = (
        supabase.table("interview_questions")
        .select("id, question, rubric, target_skills")
        .eq("interview_id", interview_id)
        .order("order_index", desc=False)
        .execute()
    )

    if not questions_row.data:
        raise HTTPException(400, "This interview has no questions. Add at least one question first.")

    questions = [
        QuestionInput(
            id=            row["id"],
            text=          row["question"],
            rubric=        row.get("rubric"),
            target_skills= row.get("target_skills") or [],
        )
        for row in questions_row.data
    ]

    # save uploaded video to a temp file
    suffix = Path(video.filename).suffix or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(video.file, tmp)
        tmp_path = tmp.name

    try:
        payload = AnalysisRequest(
            interview_id=    interview_id,
            video_url=       tmp_path,
            questions=       questions,
            scoring_weights= None,
        )
        report = run_analysis(payload)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"Analysis failed: {str(e)}")
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    try:
        supabase.table("analysis_results").upsert({
            "interview_id":  report.interview_id,
            "overall_score": report.overall_score,
            "relevance":     report.relevance.model_dump(),
            "soft_skills":   report.soft_skills.model_dump(),
            "generated_at":  report.generated_at.isoformat(),
        }, on_conflict="interview_id").execute()
    except Exception:
        traceback.print_exc()

    return report