from app.config import settings


def _empty_emotion_bucket() -> dict[str, float]:
    return {}


def _accumulate_emotion(bucket: dict[str, float], emotion: dict) -> None:
    for name, value in emotion.items():
        try:
            bucket[name] = bucket.get(name, 0.0) + float(value)
        except (TypeError, ValueError):
            continue


def _normalize_bucket(bucket: dict[str, float], sample_count: int) -> dict[str, float]:
    if sample_count <= 0:
        return {}
    return {k: v / sample_count for k, v in bucket.items()}


def _dominant_emotion(distribution: dict[str, float]) -> tuple[str, float]:
    if not distribution:
        return "unknown", 0.0
    name, conf = max(distribution.items(), key=lambda item: float(item[1]))
    return str(name), round(float(conf) * 100.0, 1)


def _bucketize(valid_with_ts: list[tuple[float, dict]]) -> list[dict]:
    window_sec = max(1.0, float(settings.video_timeline_window_sec))
    if not valid_with_ts:
        return []

    ordered = sorted(valid_with_ts, key=lambda item: float(item[0]))
    buckets: list[dict] = []

    current_idx: int | None = None
    current_sum: dict[str, float] = _empty_emotion_bucket()
    current_samples = 0

    for ts, pred in ordered:
        emotion = pred.get("emotion", {}) or {}
        if not emotion:
            continue

        idx = int(float(ts) // window_sec)
        if current_idx is None:
            current_idx = idx

        if idx != current_idx:
            dist = _normalize_bucket(current_sum, current_samples)
            dominant, confidence = _dominant_emotion(dist)
            bucket_mid_ts = (current_idx * window_sec) + (window_sec / 2.0)
            buckets.append(
                {
                    "timestamp_sec": round(bucket_mid_ts, 2),
                    "dominant_emotion": dominant,
                    "confidence": confidence,
                }
            )

            current_idx = idx
            current_sum = _empty_emotion_bucket()
            current_samples = 0

        _accumulate_emotion(current_sum, emotion)
        current_samples += 1

    if current_idx is not None and current_samples > 0:
        dist = _normalize_bucket(current_sum, current_samples)
        dominant, confidence = _dominant_emotion(dist)
        bucket_mid_ts = (current_idx * window_sec) + (window_sec / 2.0)
        buckets.append(
            {
                "timestamp_sec": round(bucket_mid_ts, 2),
                "dominant_emotion": dominant,
                "confidence": confidence,
            }
        )

    return buckets


def _stabilize_labels(points: list[dict]) -> list[dict]:
    if not points:
        return []

    switch_min_conf = float(settings.video_timeline_switch_confidence_min)
    stable: list[dict] = []

    for point in points:
        current_label = str(point.get("dominant_emotion", "unknown"))
        current_conf = float(point.get("confidence", 0.0))

        if not stable:
            stable.append(point)
            continue

        prev = stable[-1]
        prev_label = str(prev.get("dominant_emotion", "unknown"))

        if current_label != prev_label and current_conf < switch_min_conf:
            stable.append(
                {
                    "timestamp_sec": point["timestamp_sec"],
                    "dominant_emotion": prev_label,
                    "confidence": current_conf,
                }
            )
        else:
            stable.append(point)

    return stable


def _compress_runs(points: list[dict]) -> list[dict]:
    if not points:
        return []

    compressed = [points[0]]
    for point in points[1:]:
        if point["dominant_emotion"] == compressed[-1]["dominant_emotion"]:
            compressed[-1]["confidence"] = round(
                (float(compressed[-1]["confidence"]) + float(point["confidence"])) / 2.0,
                1,
            )
            compressed[-1]["timestamp_sec"] = point["timestamp_sec"]
        else:
            compressed.append(point)
    return compressed


def _gaze_deviation(pred: dict) -> float | None:
    gaze = pred.get("gaze")
    if not gaze:
        return None
    return (abs(float(gaze.get("yaw", 0.0))) + abs(float(gaze.get("pitch", 0.0)))) / 2.0


def build_emotion_timeline(valid_with_ts: list[tuple[float, dict]]) -> list[dict]:
    bucketed = _bucketize(valid_with_ts)
    stabilized = _stabilize_labels(bucketed)
    return _compress_runs(stabilized)


def compute_cheating_signals(raw_with_ts: list[tuple[float, dict | None]]) -> dict:
    total_frames = len(raw_with_ts)
    if total_frames == 0:
        return {
            "cheating_score": 0.0,
            "cheating_risk": "unknown",
            "cheating_flags": ["no_video_frames"],
            "looking_away_pct": 0.0,
            "no_face_pct": 100.0,
        }

    no_face_count = 0
    looking_away_count = 0
    offscreen_events = 0

    away_threshold = settings.video_gaze_max_deviation * settings.video_cheating_away_threshold_ratio
    center_threshold = settings.video_gaze_max_deviation * settings.video_cheating_center_threshold_ratio

    center_counter_sec = 0.0
    non_center_time_sec = 0.0
    center_confirmation_sec = settings.video_cheating_center_confirmation_sec
    offscreen_trigger_sec = settings.video_cheating_offscreen_trigger_sec

    ordered = sorted(raw_with_ts, key=lambda item: float(item[0]))

    for i, (ts, pred) in enumerate(ordered):
        if i < len(ordered) - 1:
            next_ts = float(ordered[i + 1][0])
            dt = max(0.05, next_ts - float(ts))
        else:
            dt = max(0.05, 1.0 / max(settings.video_frame_fps_target, 1))

        if pred is None:
            no_face_count += 1
            center_counter_sec = 0.0
            non_center_time_sec += dt
            if non_center_time_sec >= offscreen_trigger_sec:
                offscreen_events += 1
                non_center_time_sec = 0.0
            continue

        deviation = _gaze_deviation(pred)
        if deviation is not None and deviation >= away_threshold:
            looking_away_count += 1
            center_counter_sec = 0.0
            non_center_time_sec += dt
            if non_center_time_sec >= offscreen_trigger_sec:
                offscreen_events += 1
                non_center_time_sec = 0.0
            continue

        if deviation is not None and deviation <= center_threshold:
            center_counter_sec += dt
            if center_counter_sec >= center_confirmation_sec:
                non_center_time_sec = 0.0
        else:
            center_counter_sec = 0.0
            non_center_time_sec += dt
            if non_center_time_sec >= offscreen_trigger_sec:
                offscreen_events += 1
                non_center_time_sec = 0.0

    no_face_pct = round(no_face_count / total_frames * 100.0, 1)
    looking_away_pct = round(looking_away_count / total_frames * 100.0, 1)

    event_score = min(100.0, offscreen_events * settings.video_cheating_event_score_weight)
    cheating_score = round(min(100.0, 0.35 * no_face_pct + 0.45 * looking_away_pct + 0.20 * event_score), 1)

    if cheating_score >= settings.video_cheating_risk_high_min:
        cheating_risk = "high"
    elif cheating_score >= settings.video_cheating_risk_medium_min:
        cheating_risk = "medium"
    else:
        cheating_risk = "low"

    cheating_flags: list[str] = []
    if no_face_pct >= settings.video_cheating_no_face_flag_pct:
        cheating_flags.append("frequent_face_absence")
    if looking_away_pct >= settings.video_cheating_looking_away_flag_pct:
        cheating_flags.append("frequent_looking_away")
    if offscreen_events > 0:
        cheating_flags.append("sustained_offscreen_windows")
    if no_face_pct >= (settings.video_cheating_no_face_flag_pct + 20.0) and looking_away_pct >= (settings.video_cheating_looking_away_flag_pct - 5.0):
        cheating_flags.append("sustained_offscreen_behavior")

    return {
        "cheating_score": cheating_score,
        "cheating_risk": cheating_risk,
        "cheating_flags": cheating_flags,
        "looking_away_pct": looking_away_pct,
        "no_face_pct": no_face_pct,
    }
