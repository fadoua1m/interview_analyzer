import json

from app.services.gemini_client import generate
from app.schemas.analysis import QAPair, DetectedSkill, SoftSkillsResult
from app.constants.competencies import COMPETENCY_BANK
from app.analysis_pipeline.text.helpers import (
    parse_json,
    encode_transcript,
    verify_skill,
)


_EXTRACT_PROMPT = """Read this interview transcript and extract every statement
where the candidate provided concrete evidence of ability or character.

Include these evidence types — do NOT exclude role or activity statements:

  action     = what they did + what happened
               "we participated in hackathon and got to the finals"

  role       = a specific position or responsibility they held
               "I am the student editor of our college newsletter"
               "I am one of the cultural heads of the students club"

  activity   = sustained community or extracurricular involvement
               "I participated in donation camps as a Rotary Club member"

  output     = something they built or delivered
               "I built a user management project and attendance management project"

  investment = sustained effort in developing a skill
               "I have invested 3.5 years in developing my software skills"

Exclude ONLY:
  - bare self-descriptions with no example: "I am a team player", "I am focused"
  - academic scores: "I secured 9.2 CGPA"
  - generic closing lines: "I would like to join TCS"

For each statement copy the EXACT sentence — do not paraphrase.
Rate specificity:
  "concrete" = action + outcome both present
  "partial"  = role / activity / output / investment without stated outcome

Return ONLY a JSON array, no explanation:
[
  {{"quote": "exact sentence", "specificity": "concrete|partial", "type": "action|role|activity|output|investment"}},
  ...
]

Transcript:
{transcript}"""


_CLASSIFY_PROMPT = """You are a strict HR evaluator.

Evidence type → maximum strength allowed:
  action   + concrete  → "strong"   (outcome is measurable)
  action   + partial   → "moderate"
  role                 → "moderate" (responsibility without outcome)
  activity             → "moderate"
  output   (no result) → "weak"
  investment           → "moderate"

These are hard ceilings. You CANNOT assign "strong" to a role, activity, or
output without a stated measurable outcome.

Correct competency examples:
  "hackathon finals"        → team_orientation    (team + outcome)
  "student editor"          → communication       (writing/editing role)
  "cultural head"           → coordination        (organising role)
  "donation camps"          → compassion          (NOT service_orientation)
  "built projects"          → problem_solving     (output, no outcome)
  "3.5 years developing"    → willingness_to_learn

Wrong:
  "I am a team player"      → REJECT (self-description)
  "donation camps"          → service_orientation  WRONG — use compassion

Evidence list:
{evidence_list}

Competency definitions:
{competency_definitions}

Think step by step:

Step 1 — MATCH: For each evidence item, which one competency does it prove?
  Apply ceiling rules. One quote → one competency maximum.

Step 2 — DEDUPLICATE: Each competency appears once.
  If two items match the same competency keep the stronger evidence.

Step 3 — CALIBRATE: Apply ceiling, then choose exact strength within it.

Step 4 — LIMIT to maximum 5. Return fewer if evidence is weak.

Return ONLY valid JSON:
{{
  "reasoning": {{
    "step1": "<one line per match: quote → competency, ceiling applied>",
    "step2": "<what was dropped and why>",
    "step3": "<final strength for each and why>"
  }},
  "detected": [
    {{
      "name":        "<exact key from competency definitions>",
      "strength":    "weak|moderate|strong",
      "quote":       "<exact sentence from evidence list>",
      "description": "<one sentence: what they did that proves this>"
    }}
  ],
  "summary": "<2-3 sentences on what this candidate genuinely demonstrated>"
}}"""


_REFLECT_PROMPT = """You are a skeptical HR auditor checking a junior analyst's work.
3 honest results is better than 5 questionable ones.

Evidence the analyst had:
{evidence_list}

Analyst output:
{first_draft}

Check every detected skill:

1. FABRICATION — is the quote in the evidence list word for word?
   If not → mark FABRICATED and remove it.

2. INFLATION — is strength "strong" but no measurable outcome in the quote?
   If yes → mark INFLATED, downgrade to "moderate".

3. VAGUE — does the quote describe what they DID or what they ARE?
   "I am X" with no example → mark VAGUE and remove.

4. WRONG COMPETENCY — does the quote match the competency definition?
   "donation camps" → compassion YES / service_orientation NO
   If wrong → mark WRONG_COMPETENCY and reassign or remove.

Return ONLY valid JSON:
{{
  "audit": [
    {{
      "name":   "<skill>",
      "status": "VERIFIED|FABRICATED|INFLATED|VAGUE|WRONG_COMPETENCY",
      "reason": "<one sentence>",
      "fix":    "<corrected strength or correct competency key, else null>"
    }}
  ],
  "corrected": [
    {{
      "name":        "<VERIFIED skills only, with fixes applied>",
      "strength":    "weak|moderate|strong",
      "quote":       "<exact verified quote>",
      "description": "<one sentence>"
    }}
  ],
  "issues_found": true or false,
  "summary": "<2-3 sentences on what was genuinely evidenced>"
}}"""


def run(qa_pairs: list[QAPair]) -> SoftSkillsResult:
    if not qa_pairs:
        return SoftSkillsResult(detected=[], summary="No transcript available.")

    transcript = "\n\n".join(f"Q: {p.question}\nA: {p.answer}" for p in qa_pairs)
    comp_defs  = "\n".join(f"- {k}: {v}" for k, v in COMPETENCY_BANK.items())

    # ── Turn 1: extract grounded evidence ────────────────────────────────────
    try:
        raw      = parse_json(generate(_EXTRACT_PROMPT.format(transcript=transcript[:8000])))
        evidence = raw if isinstance(raw, list) else []
    except Exception as e:
        print(f"[Extract] FAILED: {e}")
        evidence = []

    print(f"[Extract] {len(evidence)} items")
    for item in evidence:
        print(f"[Extract]   [{item.get('type','?')}][{item.get('specificity','?')}] {item.get('quote','')}")

    if not evidence:
        return SoftSkillsResult(detected=[], summary="No concrete evidence found in transcript.")

    evidence_fmt = "\n".join(
        f"- [{e.get('specificity','partial').upper()}][{e.get('type','action').upper()}] "
        f"{e.get('quote','') if isinstance(e, dict) else e}"
        for e in evidence
    )

    # ── Turn 2: CoT classification ────────────────────────────────────────────
    try:
        draft = parse_json(generate(
            _CLASSIFY_PROMPT.format(
                evidence_list=evidence_fmt,
                competency_definitions=comp_defs,
            )
        ))
    except Exception as e:
        print(f"[Classify] FAILED: {e}")
        return SoftSkillsResult(detected=[], summary="Classification failed.")

    r = draft.get("reasoning", {})
    print(f"[CoT] step1: {r.get('step1','')}")
    print(f"[CoT] step2: {r.get('step2','')}")
    print(f"[CoT] step3: {r.get('step3','')}")

    # ── Turn 3: adversarial reflection ───────────────────────────────────────
    try:
        reflection = parse_json(generate(
            _REFLECT_PROMPT.format(
                evidence_list=evidence_fmt,
                first_draft=json.dumps(draft, indent=2),
            )
        ))

        for a in reflection.get("audit", []):
            print(f"[Audit] {a.get('name')}: {a.get('status')} — {a.get('reason','')}")

        if reflection.get("issues_found"):
            final_list = reflection.get("corrected", [])
            summary    = reflection.get("summary", draft.get("summary", ""))
            print("[Reflect] issues found — using corrected output")
        else:
            final_list = draft.get("detected", [])
            summary    = draft.get("summary", "")
            print("[Reflect] no issues — first draft accepted")

    except Exception as e:
        print(f"[Reflect] FAILED: {e} — using first draft")
        final_list = draft.get("detected", [])
        summary    = draft.get("summary", "")

    # ── Pre-encode transcript once for all skill verifications ────────────────
    sentences, s_embs = encode_transcript(transcript)

    # ── Three-layer verification ──────────────────────────────────────────────
    seen:   set[str]            = set()
    result: list[DetectedSkill] = []

    for item in final_list:
        name = item.get("name")
        if not name or name not in COMPETENCY_BANK:
            continue
        if name in seen:
            continue
        if not verify_skill(item, transcript, sentences, s_embs):
            continue
        seen.add(name)
        result.append(DetectedSkill(
            name=        item["name"],
            strength=    item["strength"],
            quote=       item["quote"],
            description= item["description"],
        ))

    return SoftSkillsResult(detected=result[:5], summary=summary)