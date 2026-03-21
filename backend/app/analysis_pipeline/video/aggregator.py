import numpy as np
from collections import Counter


EMOTION_LABELS = [
    "neutral", "happiness", "sadness",
    "surprise", "fear", "disgust", "anger", "contempt",
]

# Positive = engaged/confident. Negative = disengaged/stressed.
EMOTION_ENGAGEMENT_WEIGHT = {
    "neutral":   0.5,   
    "happiness": 1.0,   # strongest positive signal (MIT dataset)
    "surprise":  0.3,   # weak positive — context dependent
    "contempt": -0.2,   # residual after dampening
    "disgust":  -0.2,   # residual after dampening
    "sadness":  -0.6,
    "fear":     -0.5,   # reduced from -0.7: partially overlaps with nervousness
    "anger":    -0.4,   # reduced from -0.7: partially noise after dampening
}

# Confidence signal weights for the interview context
EMOTION_CONFIDENCE_WEIGHT = {
    "neutral":   0.5,
    "happiness": 0.8,
    "surprise":  0.2,
    "contempt": -0.3,
    "disgust":  -0.2,
    "sadness":  -0.5,
    "fear":     -0.8,
    "anger":    -0.6,
}

# AU thresholds calibrated for [0, 1] model output range
AU_GENUINE_SMILE_6  = 0.20   # AU06 cheek raise — Duchenne marker
AU_GENUINE_SMILE_12 = 0.20   # AU12 lip corner pull — Duchenne marker
AU_CONCERN_4        = 0.20   # AU04 brow lowerer — concentration/worry
AU_SADNESS_15       = 0.20   # AU15 lip corner depressor
AU_SADNESS_17       = 0.20   # AU17 chin raiser
AU_NERVOUS_1        = 0.20   # AU01 inner brow raise — anxiety marker (Nature 2025)
AU_NERVOUS_2        = 0.20   # AU02 outer brow raise — anxiety marker

CONFIDENCE_THRESHOLD = 0.5


def _filter_quality(frame_results: list[dict]) -> list[dict]:
    return [
        r for r in frame_results
        if r.get("_det_confidence", 0.0) >= CONFIDENCE_THRESHOLD
    ]


def _dominant_emotion(pred: dict) -> str:
    emotion = pred.get("emotion")
    if emotion is None:
        return "neutral"
    if isinstance(emotion, dict):
        return max(emotion.items(), key=lambda x: x[1])[0].lower()
    return str(emotion).lower()


def _get_au(pred: dict, key: str) -> float:
    aus = pred.get("action_units") or {}
    return float(aus.get(key, 0.0))


def _gaze_deviation(pred: dict) -> float | None:
    gaze = pred.get("gaze")
    if not gaze:
        return None
    yaw_vals, pitch_vals = [], []
    for eye in ["left", "right"]:
        if eye in gaze:
            yaw_vals.append(abs(gaze[eye].get("yaw",   0.0)))
            pitch_vals.append(abs(gaze[eye].get("pitch", 0.0)))
    if not yaw_vals:
        return None
    return (np.mean(yaw_vals) + np.mean(pitch_vals)) / 2


# ─── Core metrics ────────────────────────────────────────────────────────────

def compute_emotion_distribution(
    frame_results: list[dict],
) -> tuple[dict[str, float], str]:
    if not frame_results:
        return {label: 0.0 for label in EMOTION_LABELS}, "unknown"

    # Accumulate softmax probabilities across frames (smoother than argmax voting)
    accum = {label: 0.0 for label in EMOTION_LABELS}
    for r in frame_results:
        emotion = r.get("emotion", {})
        for label in EMOTION_LABELS:
            accum[label] += emotion.get(label, 0.0)

    total = sum(accum.values())
    dist  = {
        label: round(accum[label] / total * 100, 1) if total > 0 else 0.0
        for label in EMOTION_LABELS
    }
    dominant = max(dist.items(), key=lambda x: x[1])[0]
    return dist, dominant


def compute_gaze_score(frame_results: list[dict]) -> float:
    deviations = [
        d for r in frame_results
        if (d := _gaze_deviation(r)) is not None
    ]
    if not deviations:
        return 5.0
    mean_dev = float(np.mean(deviations))
    # Gaze deviation in radians. 0.3 rad ≈ 17° is a reasonable "looking away" threshold.
    score = max(0.0, 1.0 - mean_dev / 0.3) * 10
    return round(score, 2)


def compute_au_signals(frame_results: list[dict]) -> dict:
    n = len(frame_results)
    if n == 0:
        return {
            "genuine_smile_pct": 0.0,
            "concern_pct":       0.0,
            "sadness_pct":       0.0,
            "nervous_pct":       0.0,
        }

    genuine_smile = sum(
        1 for r in frame_results
        if _get_au(r, "AU06") > AU_GENUINE_SMILE_6
        and _get_au(r, "AU12") > AU_GENUINE_SMILE_12
    )
    concern = sum(
        1 for r in frame_results
        if _get_au(r, "AU04") > AU_CONCERN_4
    )
    sadness = sum(
        1 for r in frame_results
        if _get_au(r, "AU15") > AU_SADNESS_15
        and _get_au(r, "AU17") > AU_SADNESS_17
    )
    nervous = sum(
        1 for r in frame_results
        if _get_au(r, "AU01") > AU_NERVOUS_1
        and _get_au(r, "AU02") > AU_NERVOUS_2
    )

    return {
        "genuine_smile_pct": round(genuine_smile / n * 100, 1),
        "concern_pct":       round(concern       / n * 100, 1),
        "sadness_pct":       round(sadness        / n * 100, 1),
        "nervous_pct":       round(nervous        / n * 100, 1),
    }


def compute_emotion_stability(frame_results: list[dict]) -> float:
    """
    Measures how consistent the dominant emotion is across frames.
    High stability = composed, low stability = emotionally erratic.
    Returns 0–10.
    """
    if len(frame_results) < 2:
        return 5.0

    labels = [_dominant_emotion(r) for r in frame_results]
    transitions = sum(1 for i in range(1, len(labels)) if labels[i] != labels[i - 1])
    transition_rate = transitions / (len(labels) - 1)
    score = max(0.0, 1.0 - transition_rate) * 10
    return round(score, 2)


def compute_confidence_score(
    distribution: dict[str, float],
    au_signals:   dict,
    gaze_score:   float,
) -> float:
    """
    Composite confidence signal for interview context.
    Combines emotion valence, gaze steadiness, and AU smile signal.
    Returns 0–10.
    """
    em_component = sum(
        EMOTION_CONFIDENCE_WEIGHT.get(label, 0.0) * pct / 100
        for label, pct in distribution.items()
    )
    em_component = (em_component + 1) / 2  # normalise to [0, 1]

    smile_bonus   = min(au_signals["genuine_smile_pct"] / 40.0, 1.0)
    nervous_penalty = min(au_signals["nervous_pct"] / 50.0, 0.3)

    score = (
        (gaze_score / 10) * 0.35 +
        em_component       * 0.40 +
        smile_bonus        * 0.15 -
        nervous_penalty    * 0.10
    ) * 10

    return round(max(0.0, min(10.0, score)), 2)


def compute_temporal_trend(
    frame_results: list[dict],
    timestamps:    list[float],
) -> dict:
    """
    Split interview into thirds and compute engagement per segment.
    Reveals if candidate warmed up, stayed consistent, or fatigued.
    Returns engagement score 0–10 for early / middle / late thirds.
    """
    if len(frame_results) < 6:
        return {"early": 5.0, "middle": 5.0, "late": 5.0}

    n      = len(frame_results)
    third  = n // 3
    segments = {
        "early":  frame_results[:third],
        "middle": frame_results[third: 2 * third],
        "late":   frame_results[2 * third:],
    }

    result = {}
    for label, seg in segments.items():
        if not seg:
            result[label] = 5.0
            continue
        gaze = compute_gaze_score(seg)
        dist, _ = compute_emotion_distribution(seg)
        em_weights = [
            EMOTION_ENGAGEMENT_WEIGHT.get(_dominant_emotion(r), 0.0)
            for r in seg
        ]
        em_component = (float(np.mean(em_weights)) + 1) / 2 if em_weights else 0.5
        result[label] = round(((gaze / 10) * 0.6 + em_component * 0.4) * 10, 2)

    return result


def compute_engagement_score(
    gaze_score:    float,
    distribution:  dict,
    au_signals:    dict,
    stability:     float,
) -> float:
    """
    Overall engagement for the full interview.
    Incorporates gaze, emotion valence, smile presence, and emotional stability.
    Returns 0–10.
    """
    em_scores = [
        EMOTION_ENGAGEMENT_WEIGHT.get(label, 0.0) * pct / 100
        for label, pct in distribution.items()
    ]
    em_component = (sum(em_scores) + 1) / 2
    smile_comp   = min(au_signals["genuine_smile_pct"] / 30.0, 1.0)
    concern_comp = min(au_signals["concern_pct"]       / 40.0, 1.0)

    score = (
        (gaze_score   / 10) * 0.35 +
        em_component        * 0.30 +
        smile_comp          * 0.15 +
        concern_comp        * 0.10 +
        (stability    / 10) * 0.10
    ) * 10

    return round(max(0.0, min(10.0, score)), 2)


def compute_interview_insights(
    distribution:  dict[str, float],
    au_signals:    dict,
    gaze_score:    float,
    stability:     float,
    trend:         dict,
    confidence:    float,
) -> dict:
    """
    Produces human-readable interview-specific insights from all signals.
    """
    insights   = []
    strengths  = []
    flags      = []

    # Gaze
    if gaze_score >= 7.0:
        strengths.append("Maintained strong eye contact throughout the interview.")
    elif gaze_score >= 5.0:
        insights.append("Eye contact was moderate — occasional gaze aversion noted.")
    else:
        flags.append("Frequent gaze aversion detected. May signal discomfort or low confidence.")

    # Smile / warmth
    smile = au_signals["genuine_smile_pct"]
    if smile >= 20.0:
        strengths.append(f"Genuine smiling detected in {smile}% of frames — candidate appeared warm and approachable.")
    elif smile >= 8.0:
        insights.append(f"Occasional genuine smiling ({smile}%) — candidate was composed but reserved.")
    else:
        insights.append("Very little genuine smiling — candidate may have appeared tense or overly formal.")

    # Nervousness
    nervous = au_signals["nervous_pct"]
    if nervous >= 30.0:
        flags.append(f"Brow raise pattern (AU01+AU02) in {nervous}% of frames — candidate showed signs of anxiety.")
    elif nervous >= 15.0:
        insights.append(f"Mild nervousness signals in {nervous}% of frames — within normal interview range.")

    # Stability
    if stability >= 7.5:
        strengths.append("Emotionally stable throughout — consistent facial composure.")
    elif stability < 5.0:
        flags.append("High emotional variability detected — facial expressions shifted frequently.")

    # Temporal trend
    early, mid, late = trend["early"], trend["middle"], trend["late"]
    delta = late - early
    if delta >= 0.5:
        insights.append(f"Engagement increased over the interview (early: {early}, late: {late}) — candidate warmed up well.")
    elif delta <= -1.0:
        flags.append(f"Engagement declined over the interview (early: {early}, late: {late}) — candidate may have fatigued.")
    else:
        insights.append(f"Engagement was consistent throughout (early: {early}, late: {late}).")

    # Confidence composite
    if confidence >= 7.0:
        strengths.append(f"High confidence composite score ({confidence}/10).")
    elif confidence >= 5.0:
        insights.append(f"Moderate confidence level ({confidence}/10).")
    else:
        flags.append(f"Low confidence signals detected ({confidence}/10).")

    # Dominant positive/negative emotion share
    positive = distribution.get("happiness", 0.0)
    negative = sum(distribution.get(e, 0.0) for e in ["sadness", "fear", "anger"])
    if positive >= 15.0:
        strengths.append(f"Notable happiness expression ({positive}%) — candidate appeared genuinely engaged.")
    if negative >= 15.0:
        flags.append(f"Elevated negative emotion share ({negative}%) — sadness/fear/anger combined.")

    return {
        "strengths": strengths,
        "insights":  insights,
        "flags":     flags,
    }