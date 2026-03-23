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


class VideoResult(BaseModel):
    engagement_score:     float
    gaze_score:           float
    dominant_emotion:     str
    emotion_distribution: dict[str, float]
    positivity_ratio:     float
    smile_pct:            float
    genuine_smile_pct:    float
    concern_pct:          float
    sadness_pct:          float
    nervous_pct:          float
    face_detected_pct:    float
    temporal_trend:       dict[str, float | str]
    stability_score:      float
    confidence_score:     float
    insights:             dict[str, list[str]]
    reliable:             bool


class CandidateReport(BaseModel):
    interview_id:       str
    relevance:          RelevanceResult
    soft_skills:        SoftSkillsResult
    video:              VideoResult | None = None
    overall_score:      float
    generated_at:       datetime
    transcript_preview: str = ""
    qa_pairs_count:     int = 0