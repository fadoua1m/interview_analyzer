import json
from app.services.gemini_client import generate
from app.schemas.analysis import QAPair, QuestionInput


_SEGMENT_PROMPT = """You are given a job interview transcript and an ordered list of questions the candidate answered.

Your task: extract exactly the candidate's answer to each question in order.

Return ONLY a valid JSON array — no explanation, no markdown fences:
[
  {{"question_index": 0, "answer": "...", "start_sec": 0.0, "end_sec": 0.0}},
  ...
]

If you cannot identify where an answer starts or ends, use null for start_sec and end_sec.

Questions:
{questions}

Full transcript (with word timestamps if available):
{transcript}"""


def segment_transcript(
    full_transcript: str,
    questions:       list[QuestionInput],
) -> list[QAPair]:
    """
    Uses Gemini to split the full transcript into per-question answers.
    Falls back to even split if parsing fails.
    """
    questions_fmt = "\n".join(
        f"{i}. {q.text}" for i, q in enumerate(questions)
    )

    prompt = _SEGMENT_PROMPT.format(
        questions=questions_fmt,
        transcript=full_transcript[:6000],  # stay within Gemini context limit
    )

    raw = generate(prompt)
    clean = (
        raw.strip()
        .removeprefix("```json")
        .removeprefix("```")
        .removesuffix("```")
        .strip()
    )

    try:
        segments: list[dict] = json.loads(clean)
    except Exception:
        segments = _fallback_split(full_transcript, len(questions))

    # map segments back to questions preserving rubric + target_skills
    pairs: list[QAPair] = []
    for i, q in enumerate(questions):
        match = next(
            (s for s in segments if s.get("question_index") == i), None
        )
        pairs.append(QAPair(
            question=      q.text,
            answer=        match.get("answer", "[No answer extracted]") if match else "[No answer extracted]",
            rubric=        q.rubric,
            target_skills= q.target_skills,
            start_sec=     match.get("start_sec") if match else None,
            end_sec=       match.get("end_sec")   if match else None,
        ))

    return pairs


def _fallback_split(transcript: str, n: int) -> list[dict]:
    """Divide transcript evenly across n questions when Gemini parsing fails."""
    words      = transcript.split()
    chunk_size = max(1, len(words) // n)
    return [
        {
            "question_index": i,
            "answer":         " ".join(words[i * chunk_size : (i + 1) * chunk_size]),
            "start_sec":      None,
            "end_sec":        None,
        }
        for i in range(n)
    ]