from datetime import datetime, timezone

from app.schemas.analysis import (
    AudioResult,
    RelevanceResult,
    SoftSkillsResult,
    VideoResult,
    CandidateReport,
)
from app.analysis_pipeline import video
from app.analysis_pipeline import audio


def assemble(
    interview_id: str,
    relevance:    RelevanceResult | None = None,
    soft_skills:  SoftSkillsResult | None = None,
    video:        VideoResult | None = None,
    audio:        AudioResult | None = None,  
) -> CandidateReport: 
    print(
        f"[Assemble] interview={interview_id}  "
        f"relevance={relevance.overall_score}  "
        f"soft_skills={len(soft_skills.detected)} skills  "
        f"video={'included' if video else 'excluded'}"
    )

    return CandidateReport(
        interview_id= interview_id,
        relevance=    relevance,
        soft_skills=  soft_skills,
        video=        video,
        audio=        audio,   
        generated_at= datetime.now(timezone.utc),
)