def compute_prosody(features: dict):
    pitch_var = features["pitch_std"]
    energy_var = features["rms_std"]
    speech_ratio = features["speech_ratio"]

    score = (
        0.4 * min(1, pitch_var / 50) +
        0.3 * min(1, energy_var / 0.02) +
        0.3 * speech_ratio
    ) * 100

    return {
        "score": round(score, 2),
        "pitch_variation": pitch_var,
        "energy_variation": energy_var,
    }