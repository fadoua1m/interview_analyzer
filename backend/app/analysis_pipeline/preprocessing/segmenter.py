import json
import re

from app.config import settings
from app.services.groq_client import generate
from app.schemas.analysis import QAPair, QuestionInput


_SEGMENT_PROMPT = """You are given a job interview transcript and an ordered list of questions the candidate answered.
The interview can be in English or French.

Your task: extract exactly the candidate's answer to each question in order.
Preserve the original language of each answer.

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
        transcript=_fit_transcript_window(full_transcript),
    )

    segments: list[dict] | None = None
    for attempt in range(settings.segment_llm_attempts):
        try:
            raw = generate(
                prompt if attempt == 0 else (
                    prompt + "\n\nReturn ONLY a JSON array. No prose, no markdown fences."
                )
            )
            candidate = _extract_json_array(raw)
            parsed = json.loads(candidate)
            if isinstance(parsed, list):
                segments = _normalize_segments(parsed, len(questions))
                break
        except Exception as e:
            print(f"[Segment] attempt {attempt + 1} failed: {e}")

    if segments is None:
        segments = _fallback_split(full_transcript, len(questions))
        print("[Segment] using fallback segmentation")

    # map segments back to questions preserving rubric + interview-level target skills
    pairs: list[QAPair] = []
    for i, q in enumerate(questions):
        match = next(
            (s for s in segments if s.get("question_index") == i), None
        )
        answer = match.get("answer", "") if match else ""
        answer = answer.strip() if isinstance(answer, str) else ""
        if not answer:
            answer = settings.segment_no_answer_placeholder

        pairs.append(QAPair(
            question=      q.text,
            answer=        answer,
            rubric=        q.rubric,
            target_skills= q.target_skills,
            start_sec=     match.get("start_sec") if match else None,
            end_sec=       match.get("end_sec")   if match else None,
        ))

    return pairs


def _fit_transcript_window(transcript: str) -> str:
    text = (transcript or "").strip()
    if len(text) <= settings.segment_max_transcript_chars:
        return text

    budget = settings.segment_max_transcript_chars
    head = text[: budget // 2]
    tail = text[-(budget - len(head)) :]
    return f"{head}\n\n[... transcript truncated for length ...]\n\n{tail}"


def _normalize_segments(raw_segments: list[dict], question_count: int) -> list[dict]:
    if question_count <= 0:
        return []

    cleaned: list[dict] = []
    for item in raw_segments:
        if not isinstance(item, dict):
            continue
        answer = item.get("answer", "")
        if not isinstance(answer, str):
            continue
        answer = answer.strip()
        if not answer:
            continue

        idx = item.get("question_index")
        if isinstance(idx, str) and idx.isdigit():
            idx = int(idx)
        elif not isinstance(idx, int):
            idx = None

        cleaned.append({
            "question_index": idx,
            "answer": answer,
            "start_sec": item.get("start_sec"),
            "end_sec": item.get("end_sec"),
        })

    if not cleaned:
        return _fallback_split("", question_count)

    valid_index_count = sum(
        1
        for item in cleaned
        if isinstance(item.get("question_index"), int)
        and 0 <= item["question_index"] < question_count
    )

    if valid_index_count < max(1, len(cleaned) // 2):
        return _assign_sequentially(cleaned, question_count)

    return _assign_by_index(cleaned, question_count)


def _assign_sequentially(items: list[dict], question_count: int) -> list[dict]:
    output = []
    for i in range(question_count):
        if i < len(items):
            output.append({
                "question_index": i,
                "answer": items[i]["answer"],
                "start_sec": items[i].get("start_sec"),
                "end_sec": items[i].get("end_sec"),
            })
        else:
            output.append({
                "question_index": i,
                "answer": settings.segment_no_answer_placeholder,
                "start_sec": None,
                "end_sec": None,
            })

    if len(items) > question_count:
        overflow_text = "\n\n".join(item["answer"] for item in items[question_count:]).strip()
        if overflow_text:
            if output[-1]["answer"] == settings.segment_no_answer_placeholder:
                output[-1]["answer"] = overflow_text
            else:
                output[-1]["answer"] = f"{output[-1]['answer']}\n\n{overflow_text}".strip()

    return output


def _assign_by_index(items: list[dict], question_count: int) -> list[dict]:
    assigned: list[dict | None] = [None] * question_count
    overflow: list[dict] = []

    for item in items:
        idx = item.get("question_index")
        if isinstance(idx, int) and 0 <= idx < question_count and assigned[idx] is None:
            assigned[idx] = item
        else:
            overflow.append(item)

    for i in range(question_count):
        if assigned[i] is None and overflow:
            assigned[i] = overflow.pop(0)

    if overflow:
        extra = "\n\n".join(item["answer"] for item in overflow if item.get("answer")).strip()
        if extra:
            if assigned[-1] is None:
                assigned[-1] = {"answer": extra, "start_sec": None, "end_sec": None}
            else:
                assigned[-1]["answer"] = f"{assigned[-1]['answer']}\n\n{extra}".strip()

    output = []
    for i in range(question_count):
        item = assigned[i]
        if not item:
            output.append({
                "question_index": i,
                "answer": settings.segment_no_answer_placeholder,
                "start_sec": None,
                "end_sec": None,
            })
            continue

        output.append({
            "question_index": i,
            "answer": item.get("answer", settings.segment_no_answer_placeholder),
            "start_sec": item.get("start_sec"),
            "end_sec": item.get("end_sec"),
        })

    return output


def _fallback_split(transcript: str, n: int) -> list[dict]:
    if n <= 0:
        return []

    text = (transcript or "").strip()
    if not text:
        return [
            {
                "question_index": i,
                "answer": settings.segment_no_answer_placeholder,
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
        chunks.append(settings.segment_no_answer_placeholder)

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