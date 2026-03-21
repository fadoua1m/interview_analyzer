from app.schemas.analysis import VideoResult
from app.analysis_pipeline.preprocessing.frame_extractor import extract_frames
from app.analysis_pipeline.video.face_analyser import analyse_frame
from app.analysis_pipeline.video.aggregator import (
    compute_gaze_score,
    compute_emotion_distribution,
    compute_au_signals,
    compute_emotion_stability,
    compute_confidence_score,
    compute_temporal_trend,
    compute_engagement_score,
    compute_interview_insights,
    _filter_quality,
)


def run(video_path: str) -> VideoResult:
    try:
        frames = extract_frames(video_path, fps_target=1)
    except Exception as e:
        print(f"[Video] Frame extraction FAILED: {e}")
        return _fallback()

    if not frames:
        print("[Video] No frames extracted")
        return _fallback()

    timestamps   = [ts for ts, _ in frames]
    frame_arrays = [f  for _, f  in frames]

    print(f"[Video] Running OpenFace on {len(frames)} frames")

    raw_results = [analyse_frame(frame) for frame in frame_arrays]

    # DEBUG — remove after diagnosis
    sample = [r for r in raw_results if r is not None][:3]
    for i, r in enumerate(sample):
        aus = r.get("action_units", {})
        print(f"[DEBUG] frame {i} AU values: {list(aus.values())[:6]}")
        print(f"[DEBUG] frame {i} emotion: {r.get('emotion')}")
    valid_with_ts = [
        (ts, r) for ts, r in zip(timestamps, raw_results)
        if r is not None
    ]

    total        = len(frames)
    detected     = len(valid_with_ts)
    detected_pct = round(detected / max(total, 1) * 100, 1)

    print(f"[Video] face detected in {detected_pct}% of frames ({detected}/{total})")

    if not valid_with_ts:
        return _fallback()

    valid_ts      = [ts for ts, _ in valid_with_ts]
    valid_results = [r  for _,  r in valid_with_ts]

    high_quality = _filter_quality(valid_results)
    use_results  = high_quality if len(high_quality) >= 10 else valid_results

    print(f"[Video] high-quality frames: {len(high_quality)} / {len(valid_results)}")

    gaze_score             = compute_gaze_score(use_results)
    distribution, dominant = compute_emotion_distribution(use_results)
    au_signals             = compute_au_signals(use_results)
    stability              = compute_emotion_stability(use_results)
    confidence             = compute_confidence_score(distribution, au_signals, gaze_score)
    trend                  = compute_temporal_trend(use_results, valid_ts)
    engagement             = compute_engagement_score(gaze_score, distribution, au_signals, stability)
    insights               = compute_interview_insights(
                                distribution, au_signals, gaze_score,
                                stability, trend, confidence,
                             )
    reliable = detected_pct >= 40.0

    print(f"[Video] dominant={dominant}  gaze={gaze_score}  engagement={engagement}  confidence={confidence}")
    print(f"[Video] smile={au_signals['genuine_smile_pct']}%  "
          f"concern={au_signals['concern_pct']}%  "
          f"nervous={au_signals['nervous_pct']}%  "
          f"stability={stability}")
    print(f"[Video] trend: early={trend['early']}  middle={trend['middle']}  late={trend['late']}")
    print(f"[Video] insights: {len(insights['strengths'])} strengths, "
          f"{len(insights['insights'])} insights, {len(insights['flags'])} flags")

    return VideoResult(
        engagement_score=     engagement,
        gaze_score=           gaze_score,
        dominant_emotion=     dominant,
        emotion_distribution= distribution,
        genuine_smile_pct=    au_signals["genuine_smile_pct"],
        concern_pct=          au_signals["concern_pct"],
        sadness_pct=          au_signals["sadness_pct"],
        nervous_pct=          au_signals["nervous_pct"],
        face_detected_pct=    detected_pct,
        temporal_trend=       trend,
        stability_score=      stability,
        confidence_score=     confidence,
        insights=             insights,
        reliable=             reliable,
    )


def _fallback() -> VideoResult:
    return VideoResult(
        engagement_score=     5.0,
        gaze_score=           5.0,
        dominant_emotion=     "unknown",
        emotion_distribution= {},
        genuine_smile_pct=    0.0,
        concern_pct=          0.0,
        sadness_pct=          0.0,
        nervous_pct=          0.0,
        face_detected_pct=    0.0,
        temporal_trend=       {"early": 5.0, "middle": 5.0, "late": 5.0},
        stability_score=      5.0,
        confidence_score=     5.0,
        insights=             {"strengths": [], "insights": [], "flags": []},
        reliable=             False,
    )