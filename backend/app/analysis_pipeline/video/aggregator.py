import numpy as np

from app.config import settings


EMOTION_LABELS = [
    "neutral", "happiness", "sadness",
    "surprise", "fear", "disgust", "anger", "contempt",
]


def _load_calibration_map() -> dict:
    return settings.video_score_calibration


def _apply_calibration(value: float, key: str, default_min: float = 0.0, default_max: float = 10.0) -> float:
    calibration = _load_calibration_map().get(key, {})
    if not isinstance(calibration, dict):
        return round(max(default_min, min(default_max, value)), 2)

    scale = calibration.get("scale", 1.0)
    bias = calibration.get("bias", 0.0)
    min_v = calibration.get("min", default_min)
    max_v = calibration.get("max", default_max)

    try:
        adjusted = value * float(scale) + float(bias)
        return round(max(float(min_v), min(float(max_v), adjusted)), 2)
    except (TypeError, ValueError):
        return round(max(default_min, min(default_max, value)), 2)


def filter_quality(frame_results: list[dict]) -> list[dict]:
    return [
        result for result in frame_results
        if result.get("_det_confidence", 0.0) >= settings.video_quality_confidence_threshold
    ]


def _gaze_deviation(pred: dict) -> float | None:
    gaze = pred.get("gaze")
    if not gaze:
        return None
    return (abs(gaze.get("yaw", 0.0)) + abs(gaze.get("pitch", 0.0))) / 2


def compute_emotion_distribution(
    frame_results: list[dict],
) -> tuple[dict[str, float], str]:
    if not frame_results:
        return {label: 0.0 for label in EMOTION_LABELS}, "unknown"

    accum = {label: 0.0 for label in EMOTION_LABELS}
    for result in frame_results:
        emotion = result.get("emotion", {})
        for label in EMOTION_LABELS:
            accum[label] += float(emotion.get(label, 0.0))

    total = sum(accum.values())
    distribution = {
        label: round(accum[label] / total * 100, 1) if total > 0 else 0.0
        for label in EMOTION_LABELS
    }
    dominant = max(distribution.items(), key=lambda item: item[1])[0]
    return distribution, dominant


def compute_gaze_score(frame_results: list[dict]) -> float:
    deviations = [
        deviation for result in frame_results
        if (deviation := _gaze_deviation(result)) is not None
    ]
    if not deviations:
        return 0.0

    mean_dev = float(np.mean(deviations))
    raw_score = max(0.0, 1.0 - mean_dev / settings.video_gaze_max_deviation) * 10
    return _apply_calibration(raw_score, "gaze")
