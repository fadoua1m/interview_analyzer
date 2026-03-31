import traceback
import shutil
import tempfile
from pathlib import Path
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from app.supabase_client import supabase
from app.schemas.analysis import AnalysisRequest, QuestionInput, CandidateReport
from app.analysis_pipeline.pipeline import run_analysis

router = APIRouter(prefix="/analysis", tags=["Analysis"])


def _normalize_report_payload(payload: dict, interview_id: str) -> dict:
    data = payload or {}
    reasons = data.get("decision_reasons")
    if not isinstance(reasons, list):
        reasons = [str(reasons)] if str(reasons or "").strip() else []

    generated_at = data.get("generated_at")
    if not generated_at:
        generated_at = datetime.now(timezone.utc).isoformat()

    return {
        "interview_id": data.get("interview_id") or interview_id,
        "hr_view": data.get("hr_view") or {},
        "overall_score": float(data.get("overall_score", 0.0) or 0.0),
        "decision": data.get("decision", "REVIEW"),
        "decision_reasons": reasons,
        "hr_summary": data.get("hr_summary", ""),
        "generated_at": generated_at,
        "qa_pairs_count": int(data.get("qa_pairs_count", 0) or 0),
    }


def _persist_report(report: CandidateReport, upsert: bool = False) -> None:
    payload = {
        "interview_id":   report.interview_id,
        "hr_view":        report.hr_view.model_dump(),
        "overall_score":  report.overall_score,
        "decision":       report.decision,
        "decision_reasons": report.decision_reasons,
        "hr_summary":     report.hr_summary,
        "generated_at":   report.generated_at.isoformat(),
        "qa_pairs_count": report.qa_pairs_count,
    }
    try:
        if upsert:
            supabase.table("analysis_results").upsert(
                payload, on_conflict="interview_id"
            ).execute()
        else:
            supabase.table("analysis_results").insert(payload).execute()
        print(f"[DB] Stored analysis for interview_id={report.interview_id}")
    except Exception as e:
        print(f"[DB] FAILED to store analysis for {report.interview_id}: {e}")
        traceback.print_exc()


def _get_interview_targets(interview_id: str) -> list[str]:
    row = (
        supabase.table("interviews")
        .select("target_softskills")
        .eq("id", interview_id)
        .execute()
    )
    return row.data[0].get("target_softskills") or [] if row.data else []


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

    targets   = _get_interview_targets(payload.interview_id)
    questions = [
        QuestionInput(
            id=           q.id,
            text=         q.text,
            rubric=       q.rubric,
            target_skills=targets,
        )
        for q in payload.questions
    ]

    try:
        report = run_analysis(AnalysisRequest(
            interview_id=    payload.interview_id,
            video_url=       payload.video_url,
            questions=       questions,
            scoring_weights= payload.scoring_weights,
        ))
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
        supabase.table("interviews").select("id").eq("id", interview_id).execute()
    ).data:
        raise HTTPException(404, "Interview not found")

    targets       = _get_interview_targets(interview_id)
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
            id=           row["id"],
            text=         row["question"],
            rubric=       row.get("rubric"),
            target_skills=targets,
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
    return _normalize_report_payload(row.data[0], interview_id)