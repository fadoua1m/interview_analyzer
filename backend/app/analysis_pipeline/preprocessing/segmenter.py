import json
import re

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
    Falls back to sentence-aware chunking if parsing fails.
    """
    questions_fmt = "\n".join(
        f"{i}. {q.text}" for i, q in enumerate(questions)
    )

    prompt = _SEGMENT_PROMPT.format(
        questions=questions_fmt,
        transcript=full_transcript[:9000],
    )

    segments: list[dict] | None = None
    for attempt in range(2):
        try:
            raw = generate(
                prompt if attempt == 0 else (
                    prompt + "\n\nReturn ONLY a JSON array. No prose, no markdown fences."
                )
            )
            candidate = _extract_json_array(raw)
            parsed = json.loads(candidate)
            if isinstance(parsed, list):
                segments = parsed
                break
        except Exception as e:
            print(f"[Segment] attempt {attempt + 1} failed: {e}")

    if segments is None:
        segments = _fallback_split(full_transcript, len(questions))
        print("[Segment] using fallback segmentation")

    # map segments back to questions preserving rubric + target_skills
    pairs: list[QAPair] = []
    for i, q in enumerate(questions):
        match = next(
            (s for s in segments if s.get("question_index") == i), None
        )
        answer = match.get("answer", "") if match else ""
        answer = answer.strip() if isinstance(answer, str) else ""
        if not answer:
            answer = "[No answer extracted]"

        pairs.append(QAPair(
            question=      q.text,
            answer=        answer,
            rubric=        q.rubric,
            target_skills= q.target_skills,
            start_sec=     match.get("start_sec") if match else None,
            end_sec=       match.get("end_sec")   if match else None,
        ))

    return pairs


def _fallback_split(transcript: str, n: int) -> list[dict]:
    """Fallback segmentation by sentence chunks to avoid random word slicing."""
    if n <= 0:
        return []

    text = (transcript or "").strip()
    if not text:
        return [
            {
                "question_index": i,
                "answer": "[No answer extracted]",
                "start_sec": None,
                "end_sec": None,
            }
            for i in range(n)
        ]

    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+|\n+', text) if s.strip()]
    if not sentences:
        sentences = [text]

    total_chars = sum(len(s) for s in sentences)
    target_chars = max(1, total_chars // n)

    chunks: list[str] = []
    current: list[str] = []
    current_chars = 0

    for sentence in sentences:
        if len(chunks) < n - 1 and current_chars >= target_chars and current:
            chunks.append(" ".join(current).strip())
            current = []
            current_chars = 0

        current.append(sentence)
        current_chars += len(sentence)

    if current:
        chunks.append(" ".join(current).strip())

    while len(chunks) < n:
        chunks.append("[No answer extracted]")

    return [
        {
            "question_index": i,
            "answer": chunks[i],
            "start_sec": None,
            "end_sec": None,
        }
        for i in range(n)
    ]


def _extract_json_array(raw: str) -> str:
    text = raw.strip()

    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]

    if text.endswith("```"):
        text = text[:-3]

    text = text.strip()

    # Prefer extracting the outermost JSON array when the model adds prose.
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        return text[start:end + 1]

    return text