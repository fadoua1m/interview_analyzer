from datetime import datetime, timezone
from app.schemas.analysis import (
    RelevanceResult,
    SoftSkillsResult,
    CandidateReport,
)

_STRENGTH_MAP = {"weak": 3.0, "moderate": 6.5, "strong": 9.5}

_WEIGHTS = {
    "relevance":   0.60,
    "soft_skills": 0.40,
}


def assemble(
    interview_id: str,
    relevance:    RelevanceResult,
    soft_skills:  SoftSkillsResult,
    weights:      dict[str, float] | None = None,
) -> CandidateReport:

    w     = weights or _WEIGHTS
    total = sum(w.values())
    w     = {k: v / total for k, v in w.items()}

    soft_score = (
        sum(_STRENGTH_MAP.get(s.strength, 5.0) for s in soft_skills.detected)
        / len(soft_skills.detected)
    ) if soft_skills.detected else 0.0

    overall = round(
        w["relevance"]   * relevance.overall_score +
        w["soft_skills"] * soft_score,
        2,
    )

    print(f"[Assemble] relevance={relevance.overall_score} "
          f"soft_skills={soft_score:.2f} overall={overall}")

    return CandidateReport(
        interview_id=  interview_id,
        relevance=     relevance,
        soft_skills=   soft_skills,
        overall_score= overall,
        generated_at=  datetime.now(timezone.utc),
    )