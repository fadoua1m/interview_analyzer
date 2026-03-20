from pydantic import BaseModel
from datetime import datetime


class QuestionInput(BaseModel):
    id:            str
    text:          str
    rubric:        str | None = None
    target_skills: list[str]  = []


class AnalysisRequest(BaseModel):
    interview_id:    str
    video_url:       str
    questions:       list[QuestionInput]
    scoring_weights: dict[str, float] | None = None


class QAPair(BaseModel):
    question:      str
    answer:        str
    rubric:        str | None   = None
    target_skills: list[str]    = []
    start_sec:     float | None = None
    end_sec:       float | None = None


class PreprocessingResult(BaseModel):
    full_transcript: str
    qa_pairs:        list[QAPair]


class QuestionScore(BaseModel):
    question: str
    score:    float
    band:     str | None = None
    reason:   str


class RelevanceResult(BaseModel):
    per_question:  list[QuestionScore]
    overall_score: float


class DetectedSkill(BaseModel):
    name:        str
    strength:    str
    quote:       str
    description: str


class SoftSkillsResult(BaseModel):
    detected: list[DetectedSkill]
    summary:  str


class CandidateReport(BaseModel):
    interview_id:       str
    relevance:          RelevanceResult
    soft_skills:        SoftSkillsResult
    overall_score:      float
    generated_at:       datetime
    transcript_preview: str = ""
    qa_pairs_count:     int = 0