from app.analysis_pipeline.audio.filler_detector import detect_fillers, detect_language


def compute_fluency(features: dict, text: str, language_hint: str | None = None):
    """
    Compute fluency metrics with HR-friendly scores.
    """
    words = text.split()
    wc = len(words)

    duration = features["duration"]
    speech_duration = features["speech_duration"]

    # --- Basic rates ---
    speech_rate_wps = wc / duration if duration else 0
    speech_rate_wpm = speech_rate_wps * 60.0
    articulation_rate = wc / speech_duration if speech_duration else 0
    pause_ratio = 1 - features["speech_ratio"]

    # --- Filler word analysis ---
    language = detect_language(text, hint=language_hint)
    filler_analysis = detect_fillers(text, language=language)
    filler_percentage = filler_analysis.get("filler_percentage", 0.0)
    
    # --- Sentence completion (estimate: count periods/question marks) ---
    sentence_count = max(1, text.count(".") + text.count("?") + text.count("!"))
    incomplete_sentences = max(0, sentence_count - (wc // 15))  # rough estimate
    sentence_completion_rate = max(0, (1 - (incomplete_sentences / max(sentence_count, 1))) * 100)

    # --- Speech quality metrics ---
    speech_quality_score = features.get("mfcc_smoothness", 70.0)
    
    # --- Old-style score for backward compat ---
    score = (
        0.4 * min(1, speech_rate_wps / 3.0) +
        0.3 * (1 - pause_ratio) +
        0.2 * min(1, articulation_rate / 4.0) +
        0.1 * (1 - min(1, filler_percentage / 20.0))
    ) * 100

    return {
        "score": round(score, 2),
        "speech_rate": speech_rate_wpm,
        "pause_ratio": pause_ratio,
        # HR-relevant additions
        "articulation_rate": articulation_rate,
        "filler_percentage": filler_percentage,
        "filler_count": filler_analysis.get("filler_count", 0),
        "filler_types": filler_analysis.get("filler_types", {}),
        "sentence_completion_rate": round(sentence_completion_rate, 1),
        "speech_quality_score": round(speech_quality_score, 1),
        "confidence_from_fluency": filler_analysis.get("confidence_score", 50.0),
        "language": language,
    }