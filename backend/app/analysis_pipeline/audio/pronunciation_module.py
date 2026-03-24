import os
from app.analysis_pipeline.preprocessing.audio_extractor import extract_audio

from app.analysis_pipeline.audio.features_extractor import extract_features
from app.analysis_pipeline.audio.fluency import compute_fluency
from app.analysis_pipeline.audio.prosody import compute_prosody
from app.analysis_pipeline.audio.completeness import compute_completeness
from app.analysis_pipeline.audio.accuracy import compute_accuracy
from app.analysis_pipeline.audio.scorer import aggregate


def run(video_path: str, transcript_data: dict):
    audio_path, is_temp = extract_audio(video_path)

    try:
        features = extract_features(audio_path)

        fluency = compute_fluency(features, transcript_data["clean_text"])
        prosody = compute_prosody(features)
        completeness = compute_completeness(transcript_data["clean_text"])
        accuracy = compute_accuracy(audio_path)

        return aggregate(fluency, prosody, accuracy, completeness)

    finally:
        if is_temp:
            try:
                os.unlink(audio_path)
            except:
                pass