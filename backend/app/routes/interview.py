# app/routes/interview.py
import traceback
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from app.supabase_client import supabase
from app.schemas.interview import (
    InterviewCreate,
    InterviewUpdate,
    InterviewResponse,
    InterviewWithQuestions,
    QuestionCreate,
    QuestionUpdate,
    QuestionResponse,
    GenerateQuestionsRequest,
    GenerateQuestionsResponse,
    EnhanceQuestionRequest,
    AITextResponse,
    GenerateRubricRequest,
    EnhanceRubricRequest,
)
from app.services import interview_ai
from app.constants.competencies import COMPETENCY_BANK

router = APIRouter(prefix="/interviews", tags=["Interviews"])

INTERVIEWS = "interviews"
QUESTIONS  = "interview_questions"


# ════════════════════════════════════════════════════════════════════════════
#  INTERVIEWS CRUD
# ════════════════════════════════════════════════════════════════════════════

@router.post("", response_model=InterviewResponse, status_code=201)
def create_interview(payload: InterviewCreate):
    # one-to-one: one job → one interview
    existing = (
        supabase.table(INTERVIEWS)
        .select("id")
        .eq("job_id", payload.job_id)
        .execute()
    )
    if existing.data:
        raise HTTPException(409, "This job already has an interview.")

    data         = payload.model_dump()
    data["type"] = payload.type.value

    result = supabase.table(INTERVIEWS).insert(data).execute()
    if not result.data:
        raise HTTPException(500, "Failed to create interview")
    return result.data[0]


@router.get("", response_model=list[InterviewResponse])
def list_interviews():
    result = (
        supabase.table(INTERVIEWS)
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )
    return result.data


@router.get("/job/{job_id}", response_model=InterviewResponse | None)
def get_interview_by_job(job_id: str):
    """Return the single interview for a job, or null if none exists."""
    result = (
        supabase.table(INTERVIEWS)
        .select("*")
        .eq("job_id", job_id)
        .execute()
    )
    return result.data[0] if result.data else None


@router.get("/{id}", response_model=InterviewWithQuestions)
def get_interview(id: str):
    """Return interview with all its questions ordered by order_index."""
    interview = (
        supabase.table(INTERVIEWS)
        .select("*")
        .eq("id", id)
        .execute()
    )
    if not interview.data:
        raise HTTPException(404, "Interview not found")

    questions = (
        supabase.table(QUESTIONS)
        .select("*")
        .eq("interview_id", id)
        .order("order_index", desc=False)
        .execute()
    )

    data              = interview.data[0]
    data["questions"] = questions.data or []
    return data


@router.patch("/{id}", response_model=InterviewResponse)
def update_interview(id: str, payload: InterviewUpdate):
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(400, "No fields to update")

    if "type" in data and data["type"] is not None:
        data["type"] = data["type"].value

    existing = supabase.table(INTERVIEWS).select("id").eq("id", id).execute()
    if not existing.data:
        raise HTTPException(404, "Interview not found")

    data["updated_at"] = datetime.now(timezone.utc).isoformat()

    result = supabase.table(INTERVIEWS).update(data).eq("id", id).execute()
    if not result.data:
        raise HTTPException(500, "Failed to update interview")
    return result.data[0]


@router.delete("/{id}", status_code=204)
def delete_interview(id: str):
    existing = supabase.table(INTERVIEWS).select("id").eq("id", id).execute()
    if not existing.data:
        raise HTTPException(404, "Interview not found")
    supabase.table(INTERVIEWS).delete().eq("id", id).execute()


# ════════════════════════════════════════════════════════════════════════════
#  QUESTIONS CRUD
# ════════════════════════════════════════════════════════════════════════════

@router.post("/{interview_id}/questions", response_model=QuestionResponse, status_code=201)
def create_question(interview_id: str, payload: QuestionCreate):
    existing = (
        supabase.table(INTERVIEWS)
        .select("id")
        .eq("id", interview_id)
        .execute()
    )
    if not existing.data:
        raise HTTPException(404, "Interview not found")

    data                 = payload.model_dump()
    data["interview_id"] = interview_id

    result = supabase.table(QUESTIONS).insert(data).execute()
    if not result.data:
        raise HTTPException(500, "Failed to create question")
    return result.data[0]


@router.patch("/{interview_id}/questions/{question_id}", response_model=QuestionResponse)
def update_question(interview_id: str, question_id: str, payload: QuestionUpdate):
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(400, "No fields to update")

    existing = (
        supabase.table(QUESTIONS)
        .select("id")
        .eq("id", question_id)
        .eq("interview_id", interview_id)
        .execute()
    )
    if not existing.data:
        raise HTTPException(404, "Question not found")

    result = supabase.table(QUESTIONS).update(data).eq("id", question_id).execute()
    if not result.data:
        raise HTTPException(500, "Failed to update question")
    return result.data[0]


@router.delete("/{interview_id}/questions/{question_id}", status_code=204)
def delete_question(interview_id: str, question_id: str):
    existing = (
        supabase.table(QUESTIONS)
        .select("id")
        .eq("id", question_id)
        .eq("interview_id", interview_id)
        .execute()
    )
    if not existing.data:
        raise HTTPException(404, "Question not found")
    supabase.table(QUESTIONS).delete().eq("id", question_id).execute()


# ════════════════════════════════════════════════════════════════════════════
#  AI — question generation & enhancement (belongs to interview)
# ════════════════════════════════════════════════════════════════════════════

@router.post(
    "/{interview_id}/ai/generate-questions",
    response_model=GenerateQuestionsResponse,
)
def generate_questions(interview_id: str, payload: GenerateQuestionsRequest):
    """
    Generate AI interview questions tailored to:
    - Interview type  (behavioral / technical / hr / mixed)
    - Seniority level (junior / mid / senior / lead)
    - Job description + requirements
    """
    existing = (
        supabase.table(INTERVIEWS)
        .select("id")
        .eq("id", interview_id)
        .execute()
    )
    if not existing.data:
        raise HTTPException(404, "Interview not found")

    if not payload.description.strip() and not payload.requirements.strip():
        raise HTTPException(400, "Provide at least a description or requirements")

    try:
        questions = interview_ai.generate_questions(
            title=           payload.title,
            company=         payload.company,
            interview_type=  payload.interview_type,
            seniority_level= payload.seniority_level,
            description=     payload.description,
            requirements=    payload.requirements,
            count=           payload.count,
        )
        return {"questions": questions}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"AI error: {str(e)}")


@router.post(
    "/{interview_id}/questions/{question_id}/ai/enhance",
    response_model=AITextResponse,
)
def enhance_question(interview_id: str, question_id: str, payload: EnhanceQuestionRequest):
    """Rewrite a single question to be sharper, respecting type and seniority."""
    existing = (
        supabase.table(QUESTIONS)
        .select("id")
        .eq("id", question_id)
        .eq("interview_id", interview_id)
        .execute()
    )
    if not existing.data:
        raise HTTPException(404, "Question not found")

    if not payload.question.strip():
        raise HTTPException(400, "Question cannot be empty")

    try:
        return {"result": interview_ai.enhance_question(
            title=           payload.title,
            interview_type=  payload.interview_type,
            seniority_level= payload.seniority_level,
            question=        payload.question,
        )}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"AI error: {str(e)}")
    
@router.post(
    "/{interview_id}/questions/{question_id}/ai/generate-rubric",
    response_model=AITextResponse,
)
def generate_rubric(interview_id: str, question_id: str, payload: GenerateRubricRequest):
    """Generate a 4-band scoring rubric for a question."""
    existing = (
        supabase.table(QUESTIONS)
        .select("id")
        .eq("id", question_id)
        .eq("interview_id", interview_id)
        .execute()
    )
    if not existing.data:
        raise HTTPException(404, "Question not found")

    if not payload.question.strip():
        raise HTTPException(400, "Question cannot be empty")

    try:
        return {"result": interview_ai.generate_rubric(
            question=        payload.question,
            interview_type=  payload.interview_type,
            seniority_level= payload.seniority_level,
            title=           payload.title,
        )}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"AI error: {str(e)}")


@router.post(
    "/{interview_id}/questions/{question_id}/ai/enhance-rubric",
    response_model=AITextResponse,
)
def enhance_rubric(interview_id: str, question_id: str, payload: EnhanceRubricRequest):
    """Improve an existing rubric for a question."""
    existing = (
        supabase.table(QUESTIONS)
        .select("id")
        .eq("id", question_id)
        .eq("interview_id", interview_id)
        .execute()
    )
    if not existing.data:
        raise HTTPException(404, "Question not found")

    if not payload.rubric.strip():
        raise HTTPException(400, "Rubric cannot be empty")

    try:
        return {"result": interview_ai.enhance_rubric(
            question=        payload.question,
            rubric=          payload.rubric,
            interview_type=  payload.interview_type,
            seniority_level= payload.seniority_level,
            title=           payload.title,
        )}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"AI error: {str(e)}")


