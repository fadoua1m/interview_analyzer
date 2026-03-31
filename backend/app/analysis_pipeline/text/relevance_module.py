from concurrent.futures import ThreadPoolExecutor, as_completed

from app.services.groq_client import generate
from app.schemas.analysis import QAPair, QuestionScore, RelevanceResult
import re


_PROMPT = """You are an AI-powered interviewer assistant evaluating the relevance of an interview question.

Task:
- Determine how relevant the question is to assessing the candidate.
- Use the provided candidate's answer to help contextualize the evaluation.
- Provide a single numerical score (0-10) where:
    - 0 = Completely irrelevant
    - 10 = Highly relevant

Interview Question:
"{question}"

Candidate's Answer:
"{answer}"

Output Format:
Provide only a single number between 0 and 10 representing the relevance score.
"""


_PROMPT_RUBRIC_FIT = """You are an AI-powered interviewer assistant evaluating how well an answer matches a scoring rubric.

Task:
- Determine how well the candidate's answer matches the rubric criteria.
- Provide a single numerical score (0-10) where:
    - 0 = Does not satisfy rubric expectations
    - 10 = Fully satisfies top rubric expectations

Interview Question:
"{question}"

Scoring Rubric:
"{rubric}"

Candidate's Answer:
"{answer}"

Output Format:
Provide only a single number between 0 and 10 representing the rubric-fit score.
"""


def _is_unusable_answer(answer: str) -> bool:
    text = (answer or "").strip()
    if not text:
        return True
    if text == "[No answer extracted]":
        return True
    return len(text.split()) < 6


def _clamp_score(value: float) -> float:
    return max(0.0, min(10.0, value))


def _parse_numeric_score(raw: str) -> float:
    text = (raw or "").strip()
    try:
        return _clamp_score(float(text))
    except ValueError:
        match = re.search(r"-?\d+(?:\.\d+)?", text)
        if not match:
            raise ValueError("No numeric relevance score found")
        return _clamp_score(float(match.group(0)))


def _score_relevance(pair: QAPair) -> float:
    raw = generate(_PROMPT.format(question=pair.question, answer=pair.answer))
    return round(_parse_numeric_score(raw), 1)


def _score_rubric_fit(pair: QAPair) -> float | None:
    rubric = (pair.rubric or "").strip()
    if not rubric:
        return None
    raw = generate(_PROMPT_RUBRIC_FIT.format(
        question=pair.question,
        rubric=rubric,
        answer=pair.answer,
    ))
    return round(_parse_numeric_score(raw), 1)


def _score_one(pair: QAPair) -> QuestionScore:
    if _is_unusable_answer(pair.answer):
        return QuestionScore(
            question=pair.question,
            score=0.0,
            band=None,
            reason="Insufficient answer extracted for reliable scoring.",
        )

    try:
        relevance_score = _score_relevance(pair)
        rubric_fit_score = _score_rubric_fit(pair)

        if rubric_fit_score is None:
            final = relevance_score
        else:
            final = round(0.5 * relevance_score + 0.5 * rubric_fit_score, 1)

    except Exception as e:
        print(f"[Relevance] FAILED for '{pair.question[:50]}': {e}")
        relevance_score = 2.0
        rubric_fit_score = None
        final = 2.0

    quality_label = (
        "Responses were not relevant to the question."
        if final < 4.5 else
        "Responses were partially relevant to the question."
        if final < 6.0 else
        "Responses were relevant to the question."
    )

    if rubric_fit_score is None:
        reason = f"Relevance {relevance_score:.1f}/10. {quality_label}"
    else:
        reason = (
            f"Relevance {relevance_score:.1f}/10, rubric fit {rubric_fit_score:.1f}/10, "
            f"final {final:.1f}/10. {quality_label}"
        )

    return QuestionScore(
        question=pair.question,
        score=   final,
        band=    None,
        reason=  reason,
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