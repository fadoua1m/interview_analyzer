from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED
import os
from unittest import result

from httpcore import request

from app.analysis_pipeline.preprocessing.transcriber import transcribe
from app.analysis_pipeline.preprocessing.segmenter   import segment_transcript
from app.analysis_pipeline.text.relevance_module     import run as run_relevance
from app.analysis_pipeline.text.soft_skills_module   import run as run_soft_skills
from app.analysis_pipeline.video.openface_module     import run as run_video
from app.analysis_pipeline.report_assembler          import assemble
from app.schemas.analysis import AnalysisRequest, CandidateReport
from app.analysis_pipeline.audio.pronunciation_module import run as run_audio

def run_analysis(request: AnalysisRequest) -> CandidateReport:
    result     = transcribe(request.video_url)
    clean_text = result["clean_text"]
    qa_pairs   = segment_transcript(clean_text, request.questions)

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            f_relevance   = executor.submit(run_relevance,   qa_pairs)
            f_soft_skills = executor.submit(run_soft_skills, qa_pairs)
            f_video       = executor.submit(run_video,       request.video_url)
            f_audio = executor.submit(run_audio, result["audio_path"], result)
            wait([f_audio, f_video, f_relevance, f_soft_skills], return_when=ALL_COMPLETED)

        video_result = f_video.result()
        audio_result = f_audio.result()

        report = assemble(
            interview_id= request.interview_id,
            relevance=    f_relevance.result(),
            soft_skills=  f_soft_skills.result(),
            video=        video_result if video_result.reliable else None,
            audio=        audio_result,
        )

        report.video              = video_result
        report.transcript_preview = clean_text[:500]
        report.qa_pairs_count     = len(qa_pairs)

        return report
    finally:
        if result.get("audio_is_temp"):
            try:
                os.unlink(result["audio_path"])
            except OSError:
                pass