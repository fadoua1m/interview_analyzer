from app.config import settings
from app.schemas.analysis import VideoResult, VideoProfile
from app.analysis_pipeline.preprocessing.frame_extractor import extract_frames
from app.analysis_pipeline.video.face_analyser           import analyse_frame
from app.analysis_pipeline.video.aggregator              import (
    filter_quality,
    compute_emotion_distribution,
    compute_gaze_score,
)
from app.analysis_pipeline.video.cheating_detector       import (
    build_emotion_timeline,
    compute_cheating_signals,
)


def _top_emotions(distribution: dict[str, float], top_n: int = 3) -> dict[str, float]:
    if not distribution:
        return {}
    sorted_items = sorted(distribution.items(), key=lambda item: item[1], reverse=True)
    return {name: round(float(value), 1) for name, value in sorted_items[:top_n]}


def _eye_gaze_label(gaze_score: float) -> str:
    if gaze_score >= 7.0:
        return "good_eye_contact"
    if gaze_score >= 4.0:
        return "moderate_eye_contact"
    return "limited_eye_contact"


def _band_high_medium_low(value: float, high: float, medium: float) -> str:
    if value >= high:
        return "high"
    if value >= medium:
        return "medium"
    return "low"


def _compute_recruiter_signals(distribution: dict[str, float]) -> tuple[str, str, str]:
    stress_score = (
        float(distribution.get("fear", 0.0)) +
        float(distribution.get("anger", 0.0)) +
        float(distribution.get("disgust", 0.0))
    )
    nervous_score = (
        float(distribution.get("fear", 0.0)) +
        float(distribution.get("surprise", 0.0))
    )
    comfort_score = (
        float(distribution.get("neutral", 0.0)) +
        float(distribution.get("happiness", 0.0))
    )

    stress_level = _band_high_medium_low(stress_score, high=35.0, medium=18.0)
    nervous_level = _band_high_medium_low(nervous_score, high=30.0, medium=15.0)

    if comfort_score >= 65.0:
        comfort_level = "high"
    elif comfort_score >= 45.0:
        comfort_level = "medium"
    else:
        comfort_level = "low"

    return stress_level, nervous_level, comfort_level


def _attention_level(eye_gaze: str, looking_away_pct: float) -> str:
    if eye_gaze == "good_eye_contact" and looking_away_pct <= 20.0:
        return "High"
    if eye_gaze in {"good_eye_contact", "moderate_eye_contact"} and looking_away_pct <= 40.0:
        return "Medium"
    return "Low"


def _composure_level(stress_level: str, nervous_level: str) -> str:
    if stress_level == "low" and nervous_level in {"low", "medium"}:
        return "Calm"
    if stress_level == "high" or nervous_level == "high":
        return "Stressed"
    return "Moderate"


def _recommendation(attention_level: str, composure_level: str, integrity_risk: str, reliability: bool) -> str:
    if not reliability:
        return "Video signal quality is limited; use video as secondary evidence only."
    if integrity_risk == "High":
        return "Potential integrity concerns detected; review interview segment before final decision."
    if attention_level == "High" and composure_level in {"Calm", "Moderate"} and integrity_risk == "Low":
        return "Strong on-camera presence with stable behavior and low integrity risk."
    return "Video behavior is acceptable; combine with audio and content evidence for final decision."


def _build_video_profile(
    eye_gaze: str,
    stress_level: str,
    nervous_level: str,
    cheating_risk: str,
    looking_away_pct: float,
    face_detected_pct: float,
    reliable: bool,
) -> VideoProfile:
    attention = _attention_level(eye_gaze=eye_gaze, looking_away_pct=looking_away_pct)
    composure = _composure_level(stress_level=stress_level, nervous_level=nervous_level)

    if cheating_risk == "high":
        integrity = "High"
    elif cheating_risk == "medium":
        integrity = "Medium"
    elif cheating_risk == "low":
        integrity = "Low"
    else:
        integrity = "Unknown"

    reliability_status = "Reliable" if reliable else "Not Reliable"
    recommendation = _recommendation(
        attention_level=attention,
        composure_level=composure,
        integrity_risk=integrity,
        reliability=reliable,
    )

    if eye_gaze == "good_eye_contact":
        eye_obs = "Maintains strong eye contact during the interview."
    elif eye_gaze == "moderate_eye_contact":
        eye_obs = "Maintains acceptable eye contact with occasional gaze drift."
    else:
        eye_obs = "Eye contact is limited and may reduce engagement."

    if looking_away_pct <= 10.0:
        focus_obs = "Stays focused on camera for most of the conversation."
    elif looking_away_pct <= 30.0:
        focus_obs = "Looks away occasionally while answering."
    else:
        focus_obs = "Looks away frequently, which may affect presence."

    if face_detected_pct >= 90.0:
        visibility_obs = "Candidate remains clearly visible throughout the interview."
    elif face_detected_pct >= 70.0:
        visibility_obs = "Video visibility is mostly good with minor interruptions."
    else:
        visibility_obs = "Video visibility is inconsistent and limits assessment quality."

    if composure == "Calm":
        composure_obs = "Appears calm and composed under interview pressure."
    elif composure == "Moderate":
        composure_obs = "Shows mild pressure signs but remains professional."
    else:
        composure_obs = "Shows clear pressure signs that may affect delivery."

    if integrity == "Low":
        integrity_obs = "No notable signs of suspicious off-screen behavior."
    elif integrity == "Medium":
        integrity_obs = "Some off-screen behavior observed and may need review."
    elif integrity == "High":
        integrity_obs = "Frequent off-screen behavior suggests potential integrity concerns."
    else:
        integrity_obs = "Integrity could not be confidently assessed from video signal."

    observations = [eye_obs, focus_obs, visibility_obs, composure_obs, integrity_obs]

    return VideoProfile(
        attention_level=attention,
        composure_level=composure,
        integrity_risk=integrity,
        reliability_status=reliability_status,
        key_observations=observations,
        recommendation=recommendation,
    )


def run(video_path: str) -> VideoResult:
    try:
        frames = extract_frames(video_path, fps_target=settings.video_frame_fps_target)
    except Exception as e:
        print(f"[Video] Frame extraction FAILED: {e}")
        return _fallback()

    if not frames:
        print("[Video] No frames extracted")
        return _fallback()

    timestamps   = [ts for ts, _ in frames]
    frame_arrays = [f  for _, f  in frames]

    print(f"[Video] Running OpenFace on {len(frames)} frames")

    raw_results = [analyse_frame(f) for f in frame_arrays]
    raw_with_ts = list(zip(timestamps, raw_results))

    valid_with_ts = [
        (ts, r) for ts, r in zip(timestamps, raw_results)
        if r is not None
    ]

    total        = len(frames)
    detected     = len(valid_with_ts)
    detected_pct = round(detected / max(total, 1) * 100, 1)

    print(f"[Video] face detected: {detected_pct}% ({detected}/{total})")

    if not valid_with_ts:
        return _fallback()

    valid_results = [r  for _,  r in valid_with_ts]

    high_quality = filter_quality(valid_results)
    use_results  = high_quality if len(high_quality) >= settings.video_min_high_quality_frames else valid_results

    print(f"[Video] high-quality frames: {len(high_quality)}/{len(valid_results)}")

    distribution, dominant = compute_emotion_distribution(use_results)
    emotion_timeline = build_emotion_timeline(valid_with_ts)
    top_emotions = _top_emotions(distribution)
    gaze_score = compute_gaze_score(use_results)
    eye_gaze = _eye_gaze_label(gaze_score)
    stress_level, nervous_level, comfort_level = _compute_recruiter_signals(distribution)
    cheating = compute_cheating_signals(raw_with_ts)
    reliable = detected_pct >= settings.video_face_detect_reliable_pct
    video_profile = _build_video_profile(
        eye_gaze=eye_gaze,
        stress_level=stress_level,
        nervous_level=nervous_level,
        cheating_risk=cheating["cheating_risk"],
        looking_away_pct=cheating["looking_away_pct"],
        face_detected_pct=detected_pct,
        reliable=reliable,
    )

    print(
        f"[Video] dominant={dominant} gaze={gaze_score} eye_gaze={eye_gaze} "
        f"stress={stress_level} nervous={nervous_level} comfort={comfort_level} "
        f"cheating={cheating['cheating_risk']}({cheating['cheating_score']})"
    )

    return VideoResult(
        gaze_score=           gaze_score,
        eye_gaze=             eye_gaze,
        dominant_emotion=     dominant,
        emotion_distribution= distribution,
        emotion_timeline=     emotion_timeline,
        top_emotions=         top_emotions,
        stress_level=         stress_level,
        nervous_level=        nervous_level,
        comfort_level=        comfort_level,
        cheating_score=       cheating["cheating_score"],
        cheating_risk=        cheating["cheating_risk"],
        cheating_flags=       cheating["cheating_flags"],
        looking_away_pct=     cheating["looking_away_pct"],
        no_face_pct=          cheating["no_face_pct"],
        face_detected_pct=    detected_pct,
        reliable=             reliable,
        video_profile=        video_profile,
    )


def _fallback() -> VideoResult:
    return VideoResult(
        gaze_score=           0.0,
        eye_gaze=             "unknown",
        dominant_emotion=     "unknown",
        emotion_distribution= {},
        emotion_timeline=     [],
        top_emotions=         {},
        stress_level=         "unknown",
        nervous_level=        "unknown",
        comfort_level=        "unknown",
        cheating_score=       0.0,
        cheating_risk=        "unknown",
        cheating_flags=       ["insufficient_video_signal"],
        looking_away_pct=     0.0,
        no_face_pct=          100.0,
        face_detected_pct=    0.0,
        reliable=             False,
        video_profile=        VideoProfile(
            attention_level="Low",
            composure_level="Moderate",
            integrity_risk="Unknown",
            reliability_status="Not Reliable",
            key_observations=["Insufficient video signal for reliable visual assessment."],
            recommendation="Video signal quality is limited; use video as secondary evidence only.",
        ),
    )