import numpy as np


EMOTION_LABELS = [
    "neutral", "happiness", "sadness",
    "surprise", "fear", "disgust", "anger", "contempt",
]

EMOTION_ENGAGEMENT_WEIGHT = {
    "neutral":   0.5,
    "happiness": 1.0,
    "surprise":  0.3,
    "contempt": -0.2,
    "disgust":  -0.2,
    "sadness":  -0.6,
    "fear":     -0.5,
    "anger":    -0.4,
}

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

AU_THRESHOLD = {
    "smile_6":   0.05,
    "smile_12":  0.05,
    "concern_4": 0.05,
    "sad_15":    0.05,
    "sad_17":    0.05,
    "nervous_1": 0.05,
    "nervous_2": 0.05,
}

CONFIDENCE_THRESHOLD = 0.5
GAZE_MAX_DEVIATION   = 0.5


def filter_quality(frame_results: list[dict]) -> list[dict]:
    return [
        r for r in frame_results
        if r.get("_det_confidence", 0.0) >= CONFIDENCE_THRESHOLD
    ]


def _get_au(pred: dict, key: str) -> float:
    return float((pred.get("action_units") or {}).get(key, 0.0))


def _gaze_deviation(pred: dict) -> float | None:
    gaze = pred.get("gaze")
    if not gaze:
        return None
    return (abs(gaze.get("yaw", 0.0)) + abs(gaze.get("pitch", 0.0))) / 2


def _dominant_emotion(pred: dict) -> str:
    emotion = pred.get("emotion")
    if not emotion:
        return "neutral"
    return max(emotion.items(), key=lambda x: x[1])[0]


def _emotion_vector(pred: dict) -> np.ndarray:
    emotion = pred.get("emotion", {})
    return np.array([emotion.get(label, 0.0) for label in EMOTION_LABELS])


def _compute_au_baseline(frame_results: list[dict]) -> dict[str, float]:
    au_values: dict[str, list[float]] = {}
    for r in frame_results:
        aus = r.get("action_units") or {}
        for key in aus:
            au_values.setdefault(key, []).append(float(aus[key]))
    return {
        key: float(np.percentile(vals, 20)) if vals else 0.0
        for key, vals in au_values.items()
    }


def compute_emotion_distribution(
    frame_results: list[dict],
) -> tuple[dict[str, float], str]:
    if not frame_results:
        return {label: 0.0 for label in EMOTION_LABELS}, "unknown"

    accum = {label: 0.0 for label in EMOTION_LABELS}
    for r in frame_results:
        for label in EMOTION_LABELS:
            accum[label] += r.get("emotion", {}).get(label, 0.0)

    total    = sum(accum.values())
    dist     = {
        label: round(accum[label] / total * 100, 1) if total > 0 else 0.0
        for label in EMOTION_LABELS
    }
    dominant = max(dist.items(), key=lambda x: x[1])[0]
    return dist, dominant


def compute_positivity_ratio(distribution: dict[str, float]) -> float:
    positive = distribution.get("neutral", 0.0) + distribution.get("happiness", 0.0)
    negative = sum(distribution.get(e, 0.0) for e in ["fear", "sadness", "anger"])
    total    = positive + negative
    return round(positive / total * 100, 1) if total > 0 else 50.0


def compute_gaze_score(frame_results: list[dict]) -> float:
    deviations = [
        d for r in frame_results
        if (d := _gaze_deviation(r)) is not None
    ]
    if not deviations:
        return 5.0
    mean_dev = float(np.mean(deviations))
    return round(max(0.0, 1.0 - mean_dev / GAZE_MAX_DEVIATION) * 10, 2)


def compute_au_signals(
    frame_results: list[dict],
    baseline:      dict[str, float] | None = None,
) -> dict:
    n = len(frame_results)
    if n == 0:
        return {
            k: 0.0 for k in (
                "smile_pct", "genuine_smile_pct",
                "concern_pct", "sadness_pct", "nervous_pct",
            )
        }

    def threshold(key: str, base_key: str) -> float:
        base = (baseline or {}).get(base_key, 0.0)
        return max(AU_THRESHOLD[key], base * 1.5)

    t_smile_6  = threshold("smile_6",   "AU06")
    t_smile_12 = threshold("smile_12",  "AU12")
    t_concern  = threshold("concern_4", "AU04")
    t_sad_15   = threshold("sad_15",    "AU15")
    t_sad_17   = threshold("sad_17",    "AU17")
    t_nerv_1   = threshold("nervous_1", "AU01")
    t_nerv_2   = threshold("nervous_2", "AU02")

    # any smile — AU12 alone (lip corner pull is primary visible smile component)
    any_smile = sum(
        1 for r in frame_results
        if _get_au(r, "AU12") > t_smile_12
    )

    # genuine (Duchenne) smile — AU06 + AU12 both active
    genuine_smile = sum(
        1 for r in frame_results
        if _get_au(r, "AU06") > t_smile_6 and _get_au(r, "AU12") > t_smile_12
    )

    concern = sum(1 for r in frame_results if _get_au(r, "AU04") > t_concern)

    sadness = sum(
        1 for r in frame_results
        if _get_au(r, "AU15") > t_sad_15 and _get_au(r, "AU17") > t_sad_17
    )

    nervous = sum(
        1 for r in frame_results
        if _get_au(r, "AU01") > t_nerv_1 and _get_au(r, "AU02") > t_nerv_2
    )

    return {
        "smile_pct":         round(any_smile     / n * 100, 1),
        "genuine_smile_pct": round(genuine_smile / n * 100, 1),
        "concern_pct":       round(concern        / n * 100, 1),
        "sadness_pct":       round(sadness         / n * 100, 1),
        "nervous_pct":       round(nervous         / n * 100, 1),
    }


def compute_emotion_stability(frame_results: list[dict]) -> float:
    if len(frame_results) < 2:
        return 5.0
    vectors = [_emotion_vector(r) for r in frame_results]
    sims    = []
    for i in range(1, len(vectors)):
        a, b  = vectors[i - 1], vectors[i]
        denom = np.linalg.norm(a) * np.linalg.norm(b)
        if denom > 0:
            sims.append(float(np.dot(a, b) / denom))
    return round(float(np.mean(sims)) * 10, 2) if sims else 5.0


def compute_confidence_score(
    positivity_ratio: float,
    au_signals:       dict,
    gaze_score:       float,
) -> float:
    pos_component   = positivity_ratio / 100
    smile_bonus     = min(au_signals["smile_pct"] / 40.0, 1.0)
    nervous_penalty = min(au_signals["nervous_pct"] / 50.0, 0.3)

    score = (
        (gaze_score / 10) * 0.40 +
        pos_component      * 0.45 +
        smile_bonus        * 0.15 -
        nervous_penalty    * 0.10
    ) * 10

    return round(max(0.0, min(10.0, score)), 2)


def compute_temporal_trend(
    frame_results: list[dict],
    timestamps:    list[float],
    baseline:      dict[str, float] | None = None,
) -> dict:
    if len(frame_results) < 6:
        return {"early": 5.0, "middle": 5.0, "late": 5.0, "pattern": "Stable"}

    n      = len(frame_results)
    third  = n // 3
    segs   = {
        "early":  frame_results[:third],
        "middle": frame_results[third: 2 * third],
        "late":   frame_results[2 * third:],
    }

    scores = {}
    for label, seg in segs.items():
        if not seg:
            scores[label] = 5.0
            continue
        gaze      = compute_gaze_score(seg)
        dist, _   = compute_emotion_distribution(seg)
        pos_ratio = compute_positivity_ratio(dist) / 100
        scores[label] = round(((gaze / 10) * 0.6 + pos_ratio * 0.4) * 10, 2)

    delta   = scores["late"] - scores["early"]
    pattern = "Warming" if delta >= 0.5 else ("Fatiguing" if delta <= -1.0 else "Stable")

    return {**scores, "pattern": pattern}


def compute_engagement_score(
    gaze_score:       float,
    positivity_ratio: float,
    au_signals:       dict,
    stability:        float,
) -> float:
    pos_component   = positivity_ratio / 100
    smile_comp      = min(au_signals["smile_pct"] / 30.0, 1.0)
    concern_comp    = min(au_signals["concern_pct"] / 40.0, 1.0)
    nervous_penalty = min(au_signals["nervous_pct"] / 50.0, 0.3)

    score = (
        (gaze_score  / 10) * 0.40 +
        pos_component       * 0.30 +
        smile_comp          * 0.15 +
        concern_comp        * 0.05 +
        (stability   / 10) * 0.10 -
        nervous_penalty     * 0.05
    ) * 10

    return round(max(0.0, min(10.0, score)), 2)


def compute_interview_insights(
    distribution:     dict[str, float],
    au_signals:       dict,
    gaze_score:       float,
    stability:        float,
    trend:            dict,
    confidence:       float,
    positivity_ratio: float,
) -> dict:
    strengths = []
    insights  = []
    flags     = []

    # gaze
    if gaze_score >= 7.0:
        strengths.append("Maintained strong eye contact throughout the interview.")
    elif gaze_score >= 5.0:
        insights.append("Eye contact was moderate — occasional gaze aversion noted.")
    else:
        flags.append("Frequent gaze aversion detected — may signal discomfort or low confidence.")

    # smile — use genuine_smile_pct for quality, smile_pct for presence
    genuine = au_signals["genuine_smile_pct"]
    smile   = au_signals["smile_pct"]
    if genuine >= 15.0:
        strengths.append(
            f"Genuine (Duchenne) smiling in {genuine}% of frames — "
            f"candidate appeared warm and approachable."
        )
    elif smile >= 15.0:
        insights.append(
            f"Smiling detected in {smile}% of frames — candidate appeared engaged. "
            f"Genuine smile rate was {genuine}%."
        )
    elif smile >= 5.0:
        insights.append(
            f"Occasional smiling ({smile}%) — candidate was composed but reserved."
        )
    else:
        insights.append(
            "Very little smiling detected — candidate may have appeared tense or overly formal."
        )

    # concern / concentration
    concern = au_signals["concern_pct"]
    if concern >= 20.0:
        insights.append(
            f"Brow concentration signal (AU04) in {concern}% of frames — "
            f"candidate appeared focused and engaged in thinking."
        )
    elif concern >= 10.0:
        insights.append(f"Moderate concentration signals ({concern}%) — normal interview range.")

    # nervousness
    nervous = au_signals["nervous_pct"]
    if nervous >= 30.0:
        flags.append(
            f"Anxiety signals (AU01+AU02) in {nervous}% of frames — "
            f"candidate showed signs of nervousness."
        )
    elif nervous >= 15.0:
        insights.append(
            f"Mild nervousness signals in {nervous}% of frames — within normal interview range."
        )

    # stability
    if stability >= 7.5:
        strengths.append("Emotionally stable throughout — consistent facial composure.")
    elif stability < 5.0:
        flags.append("High emotional variability — facial expressions shifted frequently.")

    # temporal trend
    early, late, pattern = trend["early"], trend["late"], trend["pattern"]
    if pattern == "Warming":
        insights.append(
            f"Engagement increased over the interview "
            f"(early: {early} → late: {late}) — candidate warmed up well."
        )
    elif pattern == "Fatiguing":
        flags.append(
            f"Engagement declined over the interview "
            f"(early: {early} → late: {late}) — candidate may have fatigued."
        )
    else:
        insights.append(
            f"Engagement was consistent throughout (early: {early}, late: {late})."
        )

    # confidence
    if confidence >= 7.0:
        strengths.append(f"High confidence composite score ({confidence}/10).")
    elif confidence >= 5.0:
        insights.append(f"Moderate confidence level ({confidence}/10).")
    else:
        flags.append(f"Low confidence signals detected ({confidence}/10).")

    # positivity
    if positivity_ratio >= 70.0:
        strengths.append(
            f"Predominantly positive/neutral expression ({positivity_ratio}% of frames)."
        )
    elif positivity_ratio < 50.0:
        flags.append(
            f"Negative emotions dominant in {round(100 - positivity_ratio, 1)}% of frames."
        )

    # sadness
    sadness = au_signals["sadness_pct"]
    if sadness >= 15.0:
        flags.append(
            f"Sadness markers (AU15+AU17) detected in {sadness}% of frames — "
            f"candidate may have appeared low-energy."
        )

    insights.append(
        "Note: Nonverbal signals are influenced by cultural background. "
        "These scores should supplement, not replace, evaluation of interview content."
    )

    return {"strengths": strengths, "insights": insights, "flags": flags}