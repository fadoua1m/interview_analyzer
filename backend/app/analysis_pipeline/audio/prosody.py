def compute_prosody(features: dict):
    """
    Compute prosody metrics including HR indicators.
    """
    pitch_var = features["pitch_std"]
    energy_var = features["rms_std"]
    speech_ratio = features["speech_ratio"]
    
    # Pitch range indicator
    pitch_mean = features.get("pitch_mean", 0)
    pitch_range = max(0, pitch_var)  # proxy for pitch variation range
    
    # Long pause count (stress indicator)
    long_pause_count = features.get("long_pause_count", 0)
    
    # Energy level
    energy_level = features.get("rms_mean", 0)

    # --- Old-style score for backward compat ---
    score = (
        0.4 * min(1, pitch_var / 50) +
        0.3 * min(1, energy_var / 0.02) +
        0.3 * speech_ratio
    ) * 100

    return {
        "score": round(score, 2),
        "pitch_variation": pitch_var,
        "energy_variation": energy_var,
        # HR-relevant additions
        "pitch_mean": pitch_mean,
        "pitch_range": pitch_range,  # wider range = more engaged
        "energy_level": energy_level,
        "long_pause_count": long_pause_count,
        "speech_ratio": speech_ratio,  # ratio of speaking to silence
    }