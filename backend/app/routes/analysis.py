import traceback
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from app.supabase_client import supabase
from app.schemas.analysis import AnalysisRequest, QuestionInput, CandidateReport
from app.analysis_pipeline.pipeline import run_analysis

router = APIRouter(prefix="/analysis", tags=["Analysis"])


def _build_payload(report: CandidateReport) -> dict:
    return {
        "interview_id": report.interview_id,
        "relevance":    report.relevance.model_dump(),
        "soft_skills":  report.soft_skills.model_dump(),
        "video":        report.video.model_dump() if report.video else None,
        "generated_at": report.generated_at.isoformat(),
    }


def _persist_report(report: CandidateReport, upsert: bool = False) -> None:
    payload = _build_payload(report)
    try:
        if upsert:
            result = supabase.table("analysis_results").upsert(
                payload, on_conflict="interview_id"
            ).execute()
        else:
            result = supabase.table("analysis_results").insert(payload).execute()

        print(f"[DB] Stored analysis for interview_id={report.interview_id}")

    except Exception as e:
        # log the full error so it is visible in terminal — never silently swallow
        print(f"[DB] FAILED to store analysis for {report.interview_id}: {e}")
        traceback.print_exc()


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

    _persist_report(report, upsert=False)
    return report


@router.post("/run-upload", response_model=CandidateReport)
def run_analysis_upload(
    video:        UploadFile = File(...),
    interview_id: str        = Form(...),
):
    if not (
        supabase.table("interviews")
        .select("id")
        .eq("id", interview_id)
        .execute()
    ).data:
        raise HTTPException(404, "Interview not found")

    questions_row = (
        supabase.table("interview_questions")
        .select("id, question, rubric")
        .eq("interview_id", interview_id)
        .order("order_index", desc=False)
        .execute()
    )
    if not questions_row.data:
        raise HTTPException(400, "This interview has no questions.")

    questions = [
        QuestionInput(
            id=    row["id"],
            text=  row["question"],
            rubric=row.get("rubric"),
        )
        for row in questions_row.data
    ]

    suffix = Path(video.filename).suffix or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(video.file, tmp)
        tmp_path = tmp.name

    try:
        report = run_analysis(AnalysisRequest(
            interview_id=    interview_id,
            video_url=       tmp_path,
            questions=       questions,
            scoring_weights= None,
        ))
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"Analysis failed: {str(e)}")
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    _persist_report(report, upsert=True)
    return report


@router.get("/{interview_id}", response_model=CandidateReport)
def get_analysis(interview_id: str):
    row = (
        supabase.table("analysis_results")
        .select("*")
        .eq("interview_id", interview_id)
        .order("generated_at", desc=True)
        .limit(1)
        .execute()
    )
    if not row.data:
        raise HTTPException(404, "No analysis found for this interview")
    return row.data[0]