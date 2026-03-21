from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED

from app.analysis_pipeline.preprocessing.transcriber  import transcribe
from app.analysis_pipeline.preprocessing.segmenter    import segment_transcript
from app.analysis_pipeline.text.relevance_module      import run as run_relevance
from app.analysis_pipeline.text.soft_skills_module    import run as run_soft_skills
from app.analysis_pipeline.video.openface_module      import run as run_video
from app.analysis_pipeline.report_assembler           import assemble
from app.schemas.analysis import AnalysisRequest, PreprocessingResult, CandidateReport


def run_analysis(request: AnalysisRequest) -> CandidateReport:

    # 1. transcription + cleaning
    result     = transcribe(request.video_url)
    clean_text = result["clean_text"]

    # 2. segmentation
    qa_pairs = segment_transcript(clean_text, request.questions)

    preprocessing = PreprocessingResult(
        full_transcript=clean_text,
        qa_pairs=qa_pairs,
    )

    # 3. all modules in parallel
    with ThreadPoolExecutor(max_workers=3) as executor:
        f_relevance   = executor.submit(run_relevance,   preprocessing.qa_pairs)
        f_soft_skills = executor.submit(run_soft_skills, preprocessing.qa_pairs)
        f_video       = executor.submit(run_video,       request.video_url)
        wait([f_relevance, f_soft_skills, f_video], return_when=ALL_COMPLETED)

    video_result = f_video.result()

    # 4. assemble — exclude video from score if unreliable
    report = assemble(
        interview_id= request.interview_id,
        relevance=    f_relevance.result(),
        soft_skills=  f_soft_skills.result(),
        video=        video_result if video_result.reliable else None,
        weights=      request.scoring_weights,
    )

    # always attach video for display even if excluded from score
    report.video              = video_result
    report.transcript_preview = clean_text[:500]
    report.qa_pairs_count     = len(qa_pairs)

    return report