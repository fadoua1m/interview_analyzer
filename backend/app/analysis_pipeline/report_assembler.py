import json
from datetime import datetime, timezone

from app.services.groq_client import generate
from app.schemas.analysis import (
    AudioResult,
    RelevanceResult,
    SoftSkillsResult,
    VideoResult,
    SoftSkillEvidence,
    TextProfile,
    HRView,
    CandidateReport,
)


def _parse_json_safe(raw: str) -> dict:
    text = (raw or "").strip()

    fenced_start = text.find("```")
    if fenced_start != -1:
        fenced_end = text.find("```", fenced_start + 3)
        if fenced_end != -1:
            block = text[fenced_start + 3:fenced_end].strip()
            if block.lower().startswith("json"):
                block = block[4:].strip()
            text = block

    for candidate in [text, text[text.find("{"):text.rfind("}")+1]]:
        if not candidate:
            continue
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue

    raise json.JSONDecodeError("Unable to parse JSON from model output", text, 0)


def _short_reason(text: str, max_words: int = 12) -> str:
    clean = " ".join(str(text or "").replace("\n", " ").split()).strip(" -•")
    if not clean:
        return "Manual HR review is recommended."
    words = clean.lower().split()
    clean = " ".join(words[:max_words]).strip(" .,;") if len(words) > max_words else clean.strip(" .,;")
    return (clean[0].upper() + clean[1:] + ".") if clean else "Manual HR review is recommended."


def _top_emotions(distribution: dict[str, float], top_n: int = 3) -> dict[str, float]:
    if not distribution:
        return {}
    return {
        k: round(float(v), 1)
        for k, v in sorted(distribution.items(), key=lambda x: x[1], reverse=True)[:top_n]
    }


def _normalize_video(video: VideoResult | None) -> VideoResult | None:
    if video is None:
        return None
    dist = getattr(video, "emotion_distribution", {}) or {}
    return VideoResult(
        gaze_score=           float(getattr(video, "gaze_score", 0.0)),
        eye_gaze=             str(getattr(video, "eye_gaze", "unknown")),
        dominant_emotion=     str(getattr(video, "dominant_emotion", "unknown")),
        emotion_distribution= dist,
        emotion_timeline=     list(getattr(video, "emotion_timeline", []) or []),
        top_emotions=         getattr(video, "top_emotions", None) or _top_emotions(dist),
        stress_level=         str(getattr(video, "stress_level", "unknown")),
        nervous_level=        str(getattr(video, "nervous_level", "unknown")),
        comfort_level=        str(getattr(video, "comfort_level", "unknown")),
        cheating_score=       float(getattr(video, "cheating_score", 0.0)),
        cheating_risk=        str(getattr(video, "cheating_risk", "unknown")),
        cheating_flags=       list(getattr(video, "cheating_flags", []) or []),
        looking_away_pct=     float(getattr(video, "looking_away_pct", 0.0)),
        no_face_pct=          float(getattr(video, "no_face_pct", 0.0)),
        face_detected_pct=    float(getattr(video, "face_detected_pct", 0.0)),
        reliable=             bool(getattr(video, "reliable", False)),
        video_profile=        getattr(video, "video_profile", None),
    )


def _normalize_audio(audio: AudioResult | dict | None) -> AudioResult | None:
    if audio is None:
        return None
    if isinstance(audio, dict):
        fluency      = audio.get("fluency", {}) or {}
        prosody      = audio.get("prosody", {}) or {}
        completeness = audio.get("completeness", {}) or {}
        return AudioResult(
            overall_score=      float(audio.get("overall", 0.0)),
            fluency_score=      float(fluency["score"])       if "score" in fluency      else None,
            prosody_score=      float(prosody["score"])       if "score" in prosody      else None,
            completeness_score= float(completeness["score"]) if "score" in completeness else None,
            speech_rate=        float(fluency["speech_rate"]) if "speech_rate" in fluency else None,
            pause_ratio=        float(fluency["pause_ratio"]) if "pause_ratio" in fluency else None,
            reliable=           bool(audio.get("reliable", False)),
            quality_flags=      list(audio.get("quality_flags", []) or []),
            audio_profile=      audio.get("audio_profile"),
        )
    return AudioResult(
        overall_score=      float(getattr(audio, "overall_score", 0.0)),
        fluency_score=      getattr(audio, "fluency_score", None),
        prosody_score=      getattr(audio, "prosody_score", None),
        completeness_score= getattr(audio, "completeness_score", None),
        speech_rate=        getattr(audio, "speech_rate", None),
        pause_ratio=        getattr(audio, "pause_ratio", None),
        reliable=           bool(getattr(audio, "reliable", False)),
        quality_flags=      list(getattr(audio, "quality_flags", []) or []),
        audio_profile=      getattr(audio, "audio_profile", None),
    )


def _normalize_relevance(relevance: RelevanceResult | None) -> RelevanceResult:
    if relevance is None:
        return RelevanceResult(per_question=[], overall_score=0.0)
    return RelevanceResult(
        per_question=  list(getattr(relevance, "per_question", []) or []),
        overall_score= float(getattr(relevance, "overall_score", 0.0)),
    )


def _build_text_profile(
    relevance:   RelevanceResult,
    soft_skills: SoftSkillsResult,
) -> TextProfile:
    return TextProfile(
        relevance_score= round(float(relevance.overall_score), 2),
        softskills=[
            SoftSkillEvidence(
                name=     s.name,
                strength= s.strength,
                quote=    s.quote,
                reason=   s.description,
            )
            for s in soft_skills.detected
        ],
    )


def _build_hr_view(
    video:        VideoResult | None,
    audio:        AudioResult | None,
    text_profile: TextProfile,
) -> HRView:
    return HRView(
        video_profile= video.video_profile if video else None,
        audio_profile= audio.audio_profile if audio else None,
        text_profile=  text_profile,
    )


def _compute_overall_score(
    relevance:   RelevanceResult,
    soft_skills: SoftSkillsResult,
    audio:       AudioResult | None,
    video:       VideoResult | None,
) -> float:
    rel_score = max(0.0, min(100.0, relevance.overall_score * 10.0))

    detected = [s for s in soft_skills.detected if s.strength != "not_demonstrated"]
    if not detected:
        skills_score = 0.0
    else:
        weights        = {"weak": 40.0, "moderate": 70.0, "strong": 90.0}
        evidence_score = sum(weights.get(s.strength.lower(), 50.0) for s in detected) / len(detected)
        skills_score   = (
            round(0.6 * evidence_score + 0.4 * soft_skills.match_score, 2)
            if soft_skills.wanted else evidence_score
        )

    audio_score = max(0.0, min(100.0, audio.overall_score if audio else 0.0))

    if video is None:
        video_score = 0.0
    else:
        gaze_comp   = max(0.0, min(100.0, video.gaze_score * 10.0))
        face_comp   = max(0.0, min(100.0, video.face_detected_pct))
        cheat_pen   = max(0.0, min(100.0, video.cheating_score))
        video_score = max(0.0, min(100.0, 0.45 * gaze_comp + 0.35 * face_comp + 0.20 * (100.0 - cheat_pen)))

    total = max(1, len(relevance.per_question))
    relevant_answers = sum(1 for q in relevance.per_question if q.score >= 4.0)
    coverage_ratio   = relevant_answers / total

    relevance_penalty = 1.00 if relevance.overall_score >= 6.0 else 0.92 if relevance.overall_score >= 4.0 else 0.85
    coverage_penalty  = 0.85 + 0.15 * coverage_ratio

    overall = (
        rel_score    * 0.35 +
        skills_score * 0.30 +
        audio_score  * 0.20 +
        video_score  * 0.15
    ) * relevance_penalty * coverage_penalty

    return round(max(0.0, min(100.0, overall)), 2)


def _llm_decision(
    relevance:   RelevanceResult,
    soft_skills: SoftSkillsResult,
    video:       VideoResult | None,
    audio:       AudioResult | None,
) -> tuple[str, list[str], str]:
    total            = max(1, len(relevance.per_question))
    relevant_answers = sum(1 for q in relevance.per_question if q.score >= 4.0)

    prompt = f"""You are an HR copilot assistant. Use ONLY the provided data. Do not invent facts.
Return ONLY valid JSON (no markdown):
{{
  "decision": "PROCEED|REVIEW|REJECT",
  "decision_reasons": ["Short HR-friendly reason (max 12 words)", "...", "..."],
  "hr_summary": "3 short sentences, clear and understandable by an HR recruiter."
}}

soft_skills={json.dumps([{"name": s.name, "strength": s.strength} for s in soft_skills.detected[:5]], ensure_ascii=False)}
requested_skills={json.dumps(soft_skills.wanted, ensure_ascii=False)}
matched_skills={json.dumps(soft_skills.found_wanted, ensure_ascii=False)}
missing_skills={json.dumps(soft_skills.missing_wanted, ensure_ascii=False)}
match_score={soft_skills.match_score}
relevance_score={relevance.overall_score}
answered={relevant_answers}/{total}
video={json.dumps({"eye_gaze": video.eye_gaze, "stress_level": video.stress_level, "cheating_risk": video.cheating_risk} if video else None, ensure_ascii=False)}
audio={json.dumps({"overall_score": audio.overall_score, "quality_flags": audio.quality_flags} if audio else None, ensure_ascii=False)}
"""

    try:
        parsed          = _parse_json_safe(generate(prompt))
        decision        = str(parsed.get("decision", "REVIEW")).upper()
        if decision not in {"PROCEED", "REVIEW", "REJECT"}:
            decision    = "REVIEW"
        if relevant_answers < total and decision == "PROCEED":
            decision    = "REVIEW"
        reasons         = parsed.get("decision_reasons", [])
        decision_reasons = [_short_reason(str(r)) for r in (reasons if isinstance(reasons, list) else []) if str(r).strip()][:3]
        hr_summary       = str(parsed.get("hr_summary", "")).strip()
    except Exception as e:
        print(f"[LLM Decision] FAILED: {e}")
        decision         = "REVIEW"
        decision_reasons = ["Manual review recommended."]
        hr_summary       = "Unable to generate AI summary. Use metrics above for manual review."

    if relevance.overall_score < 4.5:
        decision_reasons = ["Low relevance score detected."] + decision_reasons
    if relevant_answers < total:
        decision_reasons = [f"Answered {relevant_answers}/{total} questions."] + decision_reasons

    decision_reasons = (decision_reasons or ["Manual review recommended."])[:3]
    hr_summary       = hr_summary or "AI copilot summary unavailable."

    return decision, decision_reasons, hr_summary


def assemble(
    interview_id: str,
    relevance:    RelevanceResult | None    = None,
    soft_skills:  SoftSkillsResult | None  = None,
    video:        VideoResult | None        = None,
    audio:        AudioResult | dict | None = None,
) -> CandidateReport:
    relevance   = _normalize_relevance(relevance)
    soft_skills = soft_skills or SoftSkillsResult(detected=[], summary="No soft skills extracted.")
    video       = _normalize_video(video)
    audio       = _normalize_audio(audio)

    overall_score              = _compute_overall_score(relevance, soft_skills, audio, video)
    decision, reasons, summary = _llm_decision(relevance, soft_skills, video, audio)
    text_profile               = _build_text_profile(relevance, soft_skills)
    hr_view                    = _build_hr_view(video, audio, text_profile)

    print(
        f"[Assemble] interview={interview_id}  "
        f"relevance={relevance.overall_score}  "
        f"skills={len(soft_skills.detected)}  "
        f"match={soft_skills.match_score}%  "
        f"decision={decision}  overall={overall_score}"
    )

    return CandidateReport(
        interview_id=     interview_id,
        hr_view=          hr_view,
        overall_score=    overall_score,
        decision=         decision,
        decision_reasons= reasons,
        hr_summary=       summary,
        generated_at=     datetime.now(timezone.utc),
    )