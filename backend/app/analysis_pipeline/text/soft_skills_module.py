import json

from app.services.groq_client import generate
from app.schemas.analysis import QAPair, DetectedSkill, SoftSkillsResult
from app.services.softskills_bank import get_competency_bank_for_language, get_softskill_keys
from app.analysis_pipeline.text.helpers import parse_json, encode_transcript, verify_skill


_EXTRACT_PROMPT = """Read this interview transcript and extract every statement
where the candidate provided concrete evidence of ability or character.
The interview can be in English or French.

Include these evidence types — do NOT exclude role or activity statements:

  action     = what they did + what happened
               "we participated in hackathon and got to the finals"
  role       = a specific position or responsibility they held
               "I am the student editor of our college newsletter"
  activity   = sustained community or extracurricular involvement
               "I participated in donation camps as a Rotary Club member"
  output     = something they built or delivered
               "I built a user management project and attendance management project"
  investment = sustained effort in developing a skill
               "I have invested 3.5 years in developing my software skills"

Exclude ONLY:
  - bare self-descriptions: "I am a team player", "I am focused"
  - academic scores: "I secured 9.2 CGPA"
  - generic closing lines: "I would like to join TCS"

Copy the EXACT sentence — do not paraphrase.
Specificity: "concrete" = action + outcome, "partial" = everything else.

Return ONLY a JSON array:
[
  {{"quote": "exact sentence", "specificity": "concrete|partial", "type": "action|role|activity|output|investment"}},
  ...
]

Transcript:
{transcript}"""


_CLASSIFY_PROMPT = """You are a strict HR evaluator.
Evidence can be in English or French.

Strength ceilings by evidence type:
  action + concrete → "strong"
  action + partial  → "moderate"
  role              → "moderate"
  activity          → "moderate"
  output            → "weak"
  investment        → "moderate"

You CANNOT assign "strong" without a measurable outcome.

Examples:
  "hackathon finals"     → team_orientation (strong)
  "student editor"       → communication (moderate)
  "cultural head"        → coordination (moderate)
  "donation camps"       → compassion (NOT service_orientation)
  "built projects"       → problem_solving (weak)
  "3.5 years developing" → willingness_to_learn (moderate)

Evidence list:
{evidence_list}

Competency definitions:
{competency_definitions}

Step 1 — MATCH: one competency per item, apply ceiling.
Step 2 — DEDUPLICATE: each competency once, keep stronger.
Step 3 — CALIBRATE: final strength within ceiling.
Step 4 — LIMIT to 5 max.

Return ONLY valid JSON:
{{
  "reasoning": {{
    "step1": "<matches>",
    "step2": "<dropped>",
    "step3": "<final strengths>"
  }},
  "detected": [
    {{
      "name":        "<competency key>",
      "strength":    "weak|moderate|strong",
      "quote":       "<exact sentence>",
      "description": "<one sentence proof>"
    }}
  ],
  "summary": "<2-3 sentences>"
}}"""


_REFLECT_PROMPT = """You are a skeptical HR auditor. 3 honest results > 5 questionable ones.

Evidence:
{evidence_list}

Analyst output:
{first_draft}

Check each detected skill:
1. FABRICATION — quote not in evidence list → remove.
2. INFLATION — "strong" with no measurable outcome → downgrade to "moderate".
3. VAGUE — "I am X" with no example → remove.
4. WRONG COMPETENCY — quote doesn't match definition → reassign or remove.

Return ONLY valid JSON:
{{
  "audit": [
    {{
      "name":   "<skill>",
      "status": "VERIFIED|FABRICATED|INFLATED|VAGUE|WRONG_COMPETENCY",
      "reason": "<one sentence>",
      "fix":    "<corrected value or null>"
    }}
  ],
  "corrected": [
    {{
      "name":        "<skill>",
      "strength":    "weak|moderate|strong",
      "quote":       "<exact quote>",
      "description": "<one sentence>"
    }}
  ],
  "issues_found": true or false,
  "summary": "<2-3 sentences>"
}}"""


def _detect_language(transcript: str) -> str:
    text = (transcript or "").lower()
    fr   = sum(text.count(m) for m in [" le ", " la ", " les ", " des ", " et ", " je ", " une "])
    en   = sum(text.count(m) for m in [" the ", " and ", " is ", " i ", " my ", " with "])
    return "fr" if fr > en else "en"


def _normalize_skill(name: str) -> str:
    return (name or "").strip().lower().replace("-", "_").replace(" ", "_")


def _load_competency_bank(language: str) -> dict[str, str]:
    bank = get_competency_bank_for_language(language)
    if bank:
        return {_normalize_skill(k): v for k, v in bank.items() if k and v}
    keys = get_softskill_keys(active_only=True)
    return {_normalize_skill(k): k.replace("_", " ") for k in keys if k}


def _apply_target_comparison(
    detected:        list[DetectedSkill],
    target_skills:   list[str],
    competency_bank: dict[str, str],
) -> tuple[list[DetectedSkill], list[str], list[str], list[str], float]:
    if not target_skills:
        return detected, [], [], [], 100.0

    detected_by_name = {s.name: s for s in detected}
    found_wanted     = [n for n in target_skills if n in detected_by_name]
    missing_wanted   = [n for n in target_skills if n not in detected_by_name]

    missing_entries = [
        DetectedSkill(
            name=        name,
            strength=    "not_demonstrated",
            quote=       "",
            description= "Requested by recruiter — no evidence found in candidate answers.",
        )
        for name in missing_wanted
        if name in competency_bank
    ]

    full_list   = detected + missing_entries
    match_score = round(len(found_wanted) / len(target_skills) * 100, 1)

    return full_list, target_skills, found_wanted, missing_wanted, match_score


def run(qa_pairs: list[QAPair]) -> SoftSkillsResult:
    if not qa_pairs:
        return SoftSkillsResult(detected=[], summary="No transcript available.")

    transcript = "\n\n".join(f"Q: {p.question}\nA: {p.answer}" for p in qa_pairs)
    comp_bank  = _load_competency_bank(_detect_language(transcript))
    comp_defs  = "\n".join(f"- {k}: {v}" for k, v in comp_bank.items())

    target_skills: list[str] = []
    seen_targets:  set[str]  = set()
    for pair in qa_pairs:
        for skill in (pair.target_skills or []):
            normalized = _normalize_skill(skill)
            if normalized and normalized in comp_bank and normalized not in seen_targets:
                seen_targets.add(normalized)
                target_skills.append(normalized)

    def _empty_result(summary: str) -> SoftSkillsResult:
        full, wanted, found, missing, score = _apply_target_comparison([], target_skills, comp_bank)
        return SoftSkillsResult(
            detected=full, summary=summary,
            wanted=wanted, found_wanted=found,
            missing_wanted=missing, match_score=score,
        )

    def _normalize_classify_output(value: object) -> tuple[dict, list[dict], str]:
        if isinstance(value, dict):
            detected = value.get("detected", [])
            if not isinstance(detected, list):
                detected = []
            summary = value.get("summary", "")
            if not isinstance(summary, str):
                summary = ""
            return value, detected, summary

        if isinstance(value, list):
            detected = [item for item in value if isinstance(item, dict)]
            return {}, detected, ""

        return {}, [], ""

    try:
        raw      = parse_json(generate(_EXTRACT_PROMPT.format(transcript=transcript[:8000])))
        evidence = raw if isinstance(raw, list) else []
    except Exception as e:
        print(f"[Extract] FAILED: {e}")
        return _empty_result("Extraction failed.")

    print(f"[Extract] {len(evidence)} items")
    for item in evidence:
        print(f"[Extract]   [{item.get('type','?')}][{item.get('specificity','?')}] {item.get('quote','')}")

    if not evidence:
        return _empty_result("No concrete evidence found in transcript.")

    evidence_fmt = "\n".join(
        f"- [{e.get('specificity','partial').upper()}][{e.get('type','action').upper()}] "
        f"{e.get('quote','') if isinstance(e, dict) else e}"
        for e in evidence
    )

    try:
        draft = parse_json(generate(
            _CLASSIFY_PROMPT.format(
                evidence_list=evidence_fmt,
                competency_definitions=comp_defs,
            )
        ))
    except Exception as e:
        print(f"[Classify] FAILED: {e}")
        return _empty_result("Classification failed.")

    draft_obj, draft_detected, draft_summary = _normalize_classify_output(draft)

    r = draft_obj.get("reasoning", {}) if isinstance(draft_obj, dict) else {}
    if not isinstance(r, dict):
        r = {}
    print(f"[CoT] step1: {r.get('step1','')}")
    print(f"[CoT] step2: {r.get('step2','')}")
    print(f"[CoT] step3: {r.get('step3','')}")

    try:
        reflection = parse_json(generate(
            _REFLECT_PROMPT.format(
                evidence_list=evidence_fmt,
                first_draft=json.dumps(draft_obj or {"detected": draft_detected, "summary": draft_summary}, indent=2),
            )
        ))

        if isinstance(reflection, dict):
            for a in reflection.get("audit", []):
                if isinstance(a, dict):
                    print(f"[Audit] {a.get('name')}: {a.get('status')} — {a.get('reason','')}")

            if reflection.get("issues_found"):
                corrected = reflection.get("corrected", [])
                final_list = corrected if isinstance(corrected, list) else draft_detected
                summary_val = reflection.get("summary", draft_summary)
                summary = summary_val if isinstance(summary_val, str) else draft_summary
                print("[Reflect] issues found — using corrected output")
            else:
                final_list = draft_detected
                summary    = draft_summary
                print("[Reflect] no issues — first draft accepted")
        else:
            final_list = draft_detected
            summary    = draft_summary
            print("[Reflect] unexpected reflection format — using first draft")

    except Exception as e:
        print(f"[Reflect] FAILED: {e} — using first draft")
        final_list = draft_detected
        summary    = draft_summary

    sentences, s_embs = encode_transcript(transcript)
    seen:   set[str]            = set()
    result: list[DetectedSkill] = []

    for item in final_list:
        if not isinstance(item, dict):
            continue
        name = _normalize_skill(item.get("name", ""))
        if not name or name not in comp_bank or name in seen:
            continue
        if not verify_skill(item, transcript, sentences, s_embs, competency_bank=comp_bank):
            continue
        seen.add(name)
        result.append(DetectedSkill(
            name=        name,
            strength=    item.get("strength", "moderate"),
            quote=       item.get("quote", ""),
            description= item.get("description", ""),
        ))

    full_list, wanted, found_wanted, missing_wanted, match_score = _apply_target_comparison(
        result[:5], target_skills, comp_bank
    )

    return SoftSkillsResult(
        detected=       full_list,
        summary=        summary,
        wanted=         wanted,
        found_wanted=   found_wanted,
        missing_wanted= missing_wanted,
        match_score=    match_score,
    )