from datetime import datetime, timezone
from app.schemas.analysis import (
    RelevanceResult,
    SoftSkillsResult,
    VideoResult,
    CandidateReport,
)

_STRENGTH_MAP = {"weak": 3.0, "moderate": 6.5, "strong": 9.5}

_WEIGHTS_WITH_VIDEO = {"relevance": 0.45, "soft_skills": 0.30, "video": 0.25}
_WEIGHTS_TEXT_ONLY  = {"relevance": 0.60, "soft_skills": 0.40}


def assemble(
    interview_id: str,
    relevance:    RelevanceResult,
    soft_skills:  SoftSkillsResult,
    video:        VideoResult | None = None,
    weights:      dict[str, float] | None = None,
) -> CandidateReport:

    include_video = video is not None and video.reliable
    w             = weights or (_WEIGHTS_WITH_VIDEO if include_video else _WEIGHTS_TEXT_ONLY)
    total         = sum(w.values())
    w             = {k: v / total for k, v in w.items()}

    soft_score = (
        sum(_STRENGTH_MAP.get(s.strength, 5.0) for s in soft_skills.detected)
        / len(soft_skills.detected)
    ) if soft_skills.detected else 0.0

    overall = round(
        w.get("relevance",   0) * relevance.overall_score +
        w.get("soft_skills", 0) * soft_score              +
        (w.get("video", 0)  * video.engagement_score if include_video else 0.0),
        2,
    )

    print(f"[Assemble] relevance={relevance.overall_score}  "
          f"soft_skills={soft_score:.2f}  "
          f"video={'excluded' if not include_video else video.engagement_score}  "
          f"overall={overall}")

    return CandidateReport(
        interview_id=  interview_id,
        relevance=     relevance,
        soft_skills=   soft_skills,
        video=         video,
        overall_score= overall,
        generated_at=  datetime.now(timezone.utc),
    )