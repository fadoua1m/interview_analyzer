import cv2
import numpy as np


def extract_frames(
    video_path:      str,
    fps_target:      int = 1,
) -> list[tuple[float, np.ndarray]]:
    """
    Extract frames at a fixed target FPS from the video.
    Default 1 frame per second — sufficient for interview analysis
    and feasible on CPU (OpenFace 3.0 processes at 38ms/frame).

    Returns list of (timestamp_seconds, frame_numpy_array).
    """
    cap      = cv2.VideoCapture(video_path)
    src_fps  = cap.get(cv2.CAP_PROP_FPS)

    if src_fps <= 0:
        cap.release()
        raise RuntimeError(f"Cannot read FPS from video: {video_path}")

    step   = max(1, int(round(src_fps / fps_target)))
    frames = []
    idx    = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if idx % step == 0:
            frames.append((round(idx / src_fps, 3), frame))
        idx += 1

    cap.release()
    print(f"[Video] Extracted {len(frames)} frames at {fps_target}fps "
          f"from {idx / max(src_fps, 1):.1f}s video")
    return frames