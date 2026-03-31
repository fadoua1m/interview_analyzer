import os
from app.config import settings
from app.analysis_pipeline.preprocessing.audio_extractor import extract_audio

from app.analysis_pipeline.audio.features_extractor import extract_features
from app.analysis_pipeline.audio.fluency import compute_fluency
from app.analysis_pipeline.audio.prosody import compute_prosody
from app.analysis_pipeline.audio.completeness import compute_completeness
from app.analysis_pipeline.audio.scorer import aggregate
from app.analysis_pipeline.audio.hr_translator import HRMetricsTranslator
from app.analysis_pipeline.audio.filler_detector import detect_language
from app.schemas.analysis import AudioProfile, ProfessionalismSignals


def run(video_path: str, transcript_data: dict):
    audio_path, is_temp = extract_audio(video_path)

    try:
        features = extract_features(audio_path)

        clean_text = transcript_data.get("clean_text", "")
        language_hint = transcript_data.get("language")

        fluency = compute_fluency(features, clean_text, language_hint=language_hint)
        prosody = compute_prosody(features)
        completeness = compute_completeness(clean_text)

        result = aggregate(fluency, prosody, completeness)

        quality_flags: list[str] = []
        duration = float(features.get("duration", 0.0))
        speech_ratio = float(features.get("speech_ratio", 0.0))
        word_count = int((completeness or {}).get("word_count", 0))

        if duration < settings.audio_min_duration_sec:
            quality_flags.append("audio_too_short")
        if word_count < settings.audio_min_word_count:
            quality_flags.append("insufficient_transcript_words")
        if speech_ratio < settings.audio_min_speech_ratio:
            quality_flags.append("low_speech_content")
        if speech_ratio > settings.audio_max_speech_ratio:
            quality_flags.append("possible_vad_or_silence_segmentation_issue")

        result["reliable"] = len(quality_flags) == 0
        result["quality_flags"] = quality_flags

        # --- Recruiter Audio Profile Generation ---
        audio_profile = _compute_audio_profile(
            fluency=fluency,
            prosody=prosody,
            features=features,
            clean_text=clean_text,
        )

        result["audio_profile"] = audio_profile

        return result

    finally:
        if is_temp:
            try:
                os.unlink(audio_path)
            except:
                pass


def _compute_audio_profile(
    fluency: dict,
    prosody: dict,
    features: dict,
    clean_text: str,
) -> AudioProfile:
    """
    Translate raw audio metrics into HR-friendly assessment.
    """
    # Extract key metrics
    filler_percentage = fluency.get("filler_percentage", 0.0)
    hesitation_count = prosody.get("long_pause_count", 0)
    pitch_range = prosody.get("pitch_range", 0.0)
    speech_rate_consistency = features.get("speech_rate_consistency", 50.0)
    
    language = detect_language(clean_text, hint=fluency.get("language"))

    # Confidence level
    confidence = HRMetricsTranslator.confidence_level(
        filler_percentage=filler_percentage,
        hesitation_count=hesitation_count,
        pitch_range=pitch_range,
        speech_rate_consistency=speech_rate_consistency,
    )
    
    # Communication clarity
    clarity = HRMetricsTranslator.communication_clarity(
        speech_rate=fluency.get("speech_rate", 0.0),
        pause_ratio=fluency.get("pause_ratio", 0.5),
        energy_variation=prosody.get("energy_variation", 0.01),
        articulation_clarity=fluency.get("speech_quality_score", 70.0),
        language=language,
    )
    
    # Response quality
    word_count = len(clean_text.split())
    expected_words = 140 if language == "fr" else 150
    response_quality = HRMetricsTranslator.response_quality(
        word_count=word_count,
        expected_word_count=expected_words,
        sentence_completion_rate=fluency.get("sentence_completion_rate", 80.0),
        speech_duration=features.get("speech_duration", 0.0),
        total_duration=features.get("duration", 1.0),
    )
    
    # Stress indicators
    stress = HRMetricsTranslator.stress_indicators(
        pitch_std=prosody.get("pitch_variation", 30.0),
        long_pause_count=hesitation_count,
        speech_rate_consistency=features.get("speech_rate_consistency", 50.0),
        energy_level=prosody.get("energy_level", 0.01),
    )
    
    # Professionalism signals
    snr_estimate = features.get("snr_estimate_db", 15.0)
    audio_clarity = min(100.0, max(0.0, (snr_estimate + 20) * 2.5))  # rough mapping
    professionalism = HRMetricsTranslator.professionalism_signals(
        audio_clarity_score=audio_clarity,
        signal_to_noise_ratio=snr_estimate,
    )

    speech_rate = fluency.get("speech_rate", 0.0)
    filler_percentage = fluency.get("filler_percentage", 0.0)
    pitch_range = prosody.get("pitch_range", 0.0)
    hesitations = prosody.get("long_pause_count", 0)
    audio_clarity_label = professionalism.get("audio_clarity", "Acceptable")

    if language == "fr":
        pace_obs = "Speech pace is well balanced for French responses." if 110 <= speech_rate <= 145 else "Speech pace could be better balanced for French responses."
    else:
        pace_obs = "Speech pace is clear and comfortable." if 120 <= speech_rate <= 150 else "Speech pace is not fully balanced yet."

    filler_obs = "Uses very few filler words." if filler_percentage < 3 else "Uses some filler words during responses."
    tone_obs = "Tone sounds engaged and confident." if pitch_range >= 40 else "Tone sounds somewhat flat at times."

    if hesitations <= 1:
        pause_obs = "Answers flow smoothly with minimal hesitation."
    elif hesitations <= 3:
        pause_obs = "Shows occasional hesitation before answering."
    else:
        pause_obs = "Frequent hesitation may affect confidence perception."

    if audio_clarity_label == "Clean":
        quality_obs = "Audio is clear and easy to understand."
    elif audio_clarity_label == "Acceptable":
        quality_obs = "Audio is understandable with minor quality limits."
    else:
        quality_obs = "Audio quality issues make evaluation harder."

    key_observations = [pace_obs, filler_obs, tone_obs, pause_obs, quality_obs]

    recommendation = HRMetricsTranslator.recommendation(
        confidence_level=confidence["level"],
        communication_clarity=clarity["level"],
        stress_indicators=stress["level"],
        audio_clarity=professionalism.get("audio_clarity", "Acceptable"),
    )

    return AudioProfile(
        confidence_level=confidence["level"],
        communication_clarity=clarity["level"],
        response_quality=response_quality["quality_level"],
        stress_indicators=stress["level"],
        professionalism_signals=ProfessionalismSignals(
            audio_clarity=professionalism.get("audio_clarity", "Acceptable"),
            environment_quality=professionalism.get("environment_quality", "Casual"),
        ),
        key_observations=key_observations,
        recommendation=recommendation,
    )