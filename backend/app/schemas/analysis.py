from pydantic import BaseModel, Field
from datetime import datetime


class QuestionInput(BaseModel):
    id:            str
    text:          str
    rubric:        str | None = None
    target_skills: list[str]  = Field(default_factory=list)


class AnalysisRequest(BaseModel):
    interview_id:    str
    video_url:       str
    questions:       list[QuestionInput]
    scoring_weights: dict[str, float] | None = None


class QAPair(BaseModel):
    question:      str
    answer:        str
    rubric:        str | None   = None
    target_skills: list[str]    = Field(default_factory=list)
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
    detected:       list[DetectedSkill]
    summary:        str
    wanted:         list[str] = Field(default_factory=list)
    found_wanted:   list[str] = Field(default_factory=list)
    missing_wanted: list[str] = Field(default_factory=list)
    match_score:    float     = 0.0


class VideoProfile(BaseModel):
    attention_level:    str       = "Medium"
    composure_level:    str       = "Moderate"
    integrity_risk:     str       = "Unknown"
    reliability_status: str       = "Not Reliable"
    key_observations:   list[str] = Field(default_factory=list)
    recommendation:     str       = ""


class VideoResult(BaseModel):
    class EmotionTimelinePoint(BaseModel):
        timestamp_sec:    float
        dominant_emotion: str
        confidence:       float

    gaze_score:           float
    eye_gaze:             str                        = "unknown"
    dominant_emotion:     str
    emotion_distribution: dict[str, float]           = Field(default_factory=dict)
    emotion_timeline:     list[EmotionTimelinePoint] = Field(default_factory=list)
    top_emotions:         dict[str, float]           = Field(default_factory=dict)
    stress_level:         str                        = "unknown"
    nervous_level:        str                        = "unknown"
    comfort_level:        str                        = "unknown"
    cheating_score:       float                      = 0.0
    cheating_risk:        str                        = "unknown"
    cheating_flags:       list[str]                  = Field(default_factory=list)
    looking_away_pct:     float                      = 0.0
    no_face_pct:          float                      = 0.0
    face_detected_pct:    float
    reliable:             bool
    video_profile:        VideoProfile | None        = None


class ProfessionalismSignals(BaseModel):
    audio_clarity:       str = "Acceptable"
    environment_quality: str = "Casual"


class AudioProfile(BaseModel):
    confidence_level:        str                    = "Medium"
    communication_clarity:   str                    = "Acceptable"
    response_quality:        float                  = 50.0
    stress_indicators:       str                    = "Moderate"
    professionalism_signals: ProfessionalismSignals = Field(default_factory=ProfessionalismSignals)
    key_observations:        list[str]              = Field(default_factory=list)
    recommendation:          str                    = ""


class AudioResult(BaseModel):
    overall_score:      float
    fluency_score:      float | None = None
    prosody_score:      float | None = None
    completeness_score: float | None = None
    speech_rate:        float | None = None
    pause_ratio:        float | None = None
    reliable:           bool         = False
    quality_flags:      list[str]    = Field(default_factory=list)
    audio_profile:      AudioProfile | None = None


class SoftSkillEvidence(BaseModel):
    name:     str
    strength: str
    quote:    str
    reason:   str


class TextProfile(BaseModel):
    relevance_score: float                    = 0.0
    softskills:      list[SoftSkillEvidence]  = Field(default_factory=list)


class HRView(BaseModel):
    video_profile: VideoProfile | None = None
    audio_profile: AudioProfile | None = None
    text_profile:  TextProfile  | None = None


class CandidateReport(BaseModel):
    interview_id:     str
    hr_view:          HRView
    overall_score:    float     = 0.0
    decision:         str       = "REVIEW"
    decision_reasons: list[str] = Field(default_factory=list)
    hr_summary:       str       = ""
    generated_at:     datetime
    qa_pairs_count:   int       = 0