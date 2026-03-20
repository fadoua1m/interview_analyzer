from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED

from app.analysis_pipeline.preprocessing.transcriber import transcribe
from app.analysis_pipeline.preprocessing.segmenter   import segment_transcript
from app.analysis_pipeline.text.relevance_module     import run as run_relevance
from app.analysis_pipeline.text.soft_skills_module   import run as run_soft_skills
from app.analysis_pipeline.report_assembler          import assemble
from app.schemas.analysis import AnalysisRequest, PreprocessingResult, CandidateReport


def run_analysis(request: AnalysisRequest) -> CandidateReport:

    # 1. transcription + cleaning
    result     = transcribe(request.video_url)
    clean_text = result["clean_text"]

    # 2. segment into QA pairs
    qa_pairs = segment_transcript(clean_text, request.questions)

    preprocessing = PreprocessingResult(
        full_transcript=clean_text,
        qa_pairs=qa_pairs,
    )

    # 3. text modules in parallel
    with ThreadPoolExecutor(max_workers=2) as executor:
        f_relevance   = executor.submit(run_relevance,   preprocessing.qa_pairs)
        f_soft_skills = executor.submit(run_soft_skills, preprocessing.qa_pairs)
        wait([f_relevance, f_soft_skills], return_when=ALL_COMPLETED)

    # 4. assemble
    report = assemble(
        interview_id=request.interview_id,
        relevance=   f_relevance.result(),
        soft_skills= f_soft_skills.result(),
        weights=     request.scoring_weights,
    )

    report.transcript_preview = clean_text[:500]
    report.qa_pairs_count     = len(qa_pairs)

    return report