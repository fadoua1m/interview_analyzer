from concurrent.futures import ThreadPoolExecutor, as_completed

from app.services.gemini_client import generate
from app.schemas.analysis import QAPair, QuestionScore, RelevanceResult
from app.analysis_pipeline.text.helpers import parse_json


_PROMPT_WITH_RUBRIC = """You are a strict interview evaluator.

Question: {question}

Rubric:
{rubric}

Candidate's answer:
{answer}

Score THREE dimensions separately then I will compute the final score.

DIMENSION 1 — CONTENT (0-10):
Did the candidate address the question?
What specific element was missing from a complete answer?

DIMENSION 2 — STRUCTURE (0-10):
Is the answer organised with a clear flow?
Or is it a disconnected list of facts?

DIMENSION 3 — RUBRIC FIT (0-10):
Which rubric band does the content fall into?
Cite one specific thing from the answer that places it there.

Return ONLY valid JSON:
{{
  "reasoning": {{
    "content":   "<what they addressed and what was missing>",
    "structure": "<organised or disconnected — one sentence>",
    "rubric":    "<which band and one specific reason>"
  }},
  "content_score":   <0-10>,
  "structure_score": <0-10>,
  "rubric_score":    <0-10>,
  "band":   "<band range only — e.g. 3-5>",
  "reason": "<one sentence: the main strength and main weakness>"
}}"""


_PROMPT_NO_RUBRIC = """You are a strict interview evaluator.

Question: {question}

Candidate's answer:
{answer}

Score THREE dimensions separately then I will compute the final score.

DIMENSION 1 — CONTENT (0-10):
Did the candidate answer the question?
0-2  = completely off topic
3-5  = partial, key elements missing
6-8  = mostly complete
9-10 = complete with depth and specifics

DIMENSION 2 — STRUCTURE (0-10):
Does the answer flow logically?
Is there a clear beginning, substance, and conclusion?
Or is it an unconnected list?

DIMENSION 3 — CLARITY (0-10):
Are key points stated clearly?
Or buried in irrelevant detail?

Return ONLY valid JSON:
{{
  "reasoning": {{
    "content":   "<what they addressed and what was missing>",
    "structure": "<organised or disconnected — one sentence>",
    "clarity":   "<clear or unclear — one sentence>"
  }},
  "content_score":   <0-10>,
  "structure_score": <0-10>,
  "clarity_score":   <0-10>,
  "band":   null,
  "reason": "<one sentence: main strength and main weakness>"
}}"""


def _score_one(pair: QAPair) -> QuestionScore:
    prompt = (
        _PROMPT_WITH_RUBRIC.format(
            question=pair.question,
            rubric=pair.rubric,
            answer=pair.answer,
        )
        if pair.rubric
        else _PROMPT_NO_RUBRIC.format(
            question=pair.question,
            answer=pair.answer,
        )
    )

    try:
        data = parse_json(generate(prompt))
    except Exception:
        try:
            data = parse_json(generate(prompt + "\n\nReturn ONLY the JSON object."))
        except Exception as e:
            print(f"[Relevance] FAILED for '{pair.question[:50]}': {e}")
            return QuestionScore(
                question=pair.question,
                score=   5.0,
                band=    None,
                reason=  "Scoring failed — defaulting to neutral score.",
            )

    r = data.get("reasoning", {})
    print(f"[Relevance] content:   {r.get('content', '')}")
    print(f"[Relevance] structure: {r.get('structure', '')}")

    # final score computed in Python — not by the LLM
    if pair.rubric:
        final = round(
            float(data.get("content_score",   5)) * 0.4 +
            float(data.get("structure_score", 5)) * 0.3 +
            float(data.get("rubric_score",    5)) * 0.3,
            1,
        )
    else:
        final = round(
            float(data.get("content_score",   5)) * 0.5 +
            float(data.get("structure_score", 5)) * 0.3 +
            float(data.get("clarity_score",   5)) * 0.2,
            1,
        )

    return QuestionScore(
        question=pair.question,
        score=   final,
        band=    data.get("band"),
        reason=  data.get("reason", ""),
    )


def run(qa_pairs: list[QAPair]) -> RelevanceResult:
    if not qa_pairs:
        return RelevanceResult(per_question=[], overall_score=0.0)

    results: list[QuestionScore | None] = [None] * len(qa_pairs)

    with ThreadPoolExecutor(max_workers=min(len(qa_pairs), 5)) as executor:
        futures = {executor.submit(_score_one, p): i for i, p in enumerate(qa_pairs)}
        for future in as_completed(futures):
            results[futures[future]] = future.result()

    overall = round(sum(r.score for r in results) / len(results), 2)
    return RelevanceResult(per_question=results, overall_score=overall)