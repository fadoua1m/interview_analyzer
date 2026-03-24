def compute_fluency(features: dict, text: str):
    words = text.split()
    wc = len(words)

    duration = features["duration"]
    speech_duration = features["speech_duration"]

    speech_rate = wc / duration if duration else 0
    articulation_rate = wc / speech_duration if speech_duration else 0
    pause_ratio = 1 - features["speech_ratio"]

    score = (
        0.5 * min(1, speech_rate / 3.0) +
        0.3 * (1 - pause_ratio) +
        0.2 * min(1, articulation_rate / 4.0)
    ) * 100

    return {
        "score": round(score, 2),
        "speech_rate": speech_rate,
        "pause_ratio": pause_ratio,
    }