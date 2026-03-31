import os
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED

from app.analysis_pipeline.preprocessing.transcriber  import transcribe
from app.analysis_pipeline.preprocessing.segmenter    import segment_transcript
from app.analysis_pipeline.text.relevance_module      import run as run_relevance
from app.analysis_pipeline.text.soft_skills_module    import run as run_soft_skills
from app.analysis_pipeline.video.openface_module      import run as run_video
from app.analysis_pipeline.audio.pronunciation_module import run as run_audio
from app.analysis_pipeline.report_assembler           import assemble
from app.schemas.analysis import AnalysisRequest, CandidateReport, RelevanceResult


def _ensure_relevance_result(relevance: RelevanceResult | None, qa_pairs_count: int) -> RelevanceResult:
    if relevance is None:
        raise RuntimeError("Relevance module did not return a result")

    if qa_pairs_count > 0 and not relevance.per_question:
        raise RuntimeError("Relevance module returned no per-question scores")

    if qa_pairs_count != len(relevance.per_question):
        raise RuntimeError(
            f"Relevance coverage mismatch: expected {qa_pairs_count} question scores, got {len(relevance.per_question)}"
        )

    return relevance


def run_analysis(request: AnalysisRequest) -> CandidateReport:
    result     = transcribe(request.video_url)
    clean_text = result["clean_text"]
    qa_pairs   = segment_transcript(clean_text, request.questions)

    try:
        with ThreadPoolExecutor(max_workers=4) as executor:
            f_relevance   = executor.submit(run_relevance,   qa_pairs)
            f_soft_skills = executor.submit(run_soft_skills, qa_pairs)
            f_video       = executor.submit(run_video,       request.video_url)
            f_audio       = executor.submit(run_audio,       result["audio_path"], result)
            wait([f_relevance, f_soft_skills, f_video, f_audio], return_when=ALL_COMPLETED)

        relevance_result = _ensure_relevance_result(f_relevance.result(), len(qa_pairs))
        print(f"[Pipeline] Relevance executed for {len(relevance_result.per_question)}/{len(qa_pairs)} questions")

        report = assemble(
            interview_id= request.interview_id,
            relevance=    relevance_result,
            soft_skills=  f_soft_skills.result(),
            video=        f_video.result(),
            audio=        f_audio.result(),
        )

        report.qa_pairs_count = len(qa_pairs)
        return report

    finally:
        if result.get("audio_is_temp"):
            try:
                os.unlink(result["audio_path"])
            except OSError:
                pass