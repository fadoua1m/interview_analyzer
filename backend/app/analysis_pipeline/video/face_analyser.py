import sys
import cv2
import numpy as np
import tempfile
import os
import torch
from functools import lru_cache
from pathlib import Path

from app.config import settings


EMOTION_INDEX = [
    "neutral", "happiness", "sadness",
    "surprise", "fear", "disgust", "anger", "contempt",
]

AU_NAMES = [
    "AU01", "AU02", "AU04", "AU05", "AU06", "AU07",
    "AU09", "AU10", "AU12", "AU14", "AU15", "AU17",
    "AU20", "AU23", "AU25", "AU26", "AU28", "AU45",
]

NOISE_FLOOR = 0.05

EMOTION_DAMPENING = {
    "contempt": 0.05,
    "disgust":  0.10,
    "anger":    0.30,
    "fear":     0.40,
    "surprise": 0.40,
}


@lru_cache(maxsize=1)
def _load_models():
    video_dir     = Path(__file__).resolve().parent
    weights       = video_dir / "weights"
    original_argv = sys.argv[:]
    original_cwd  = Path.cwd()

    try:
        sys.argv = [sys.argv[0]]
        os.chdir(video_dir)

        from openface.face_detection  import FaceDetector
        from openface.multitask_model import MultitaskPredictor

        detector  = FaceDetector(
            model_path=str(weights / "Alignment_RetinaFace.pth"),
            device="cpu",
            vis_threshold=0.5,
        )
        predictor = MultitaskPredictor(
            model_path=str(weights / "MTL_backbone.pth"),
            device="cpu",
        )
    finally:
        sys.argv = original_argv
        os.chdir(original_cwd)

    return detector, predictor


def analyse_frame(frame: np.ndarray) -> dict | None:
    tmp_path = None
    try:
        detector, predictor = _load_models()

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp_path = tmp.name
            cv2.imwrite(tmp_path, frame)

        cropped_face, dets = detector.get_face(tmp_path)
        if cropped_face is None or dets is None:
            return None

        emotion_logits, gaze_output, au_output = predictor.predict(cropped_face)

        probs = torch.softmax(emotion_logits, dim=1)[0].detach().cpu().numpy().copy()
        for i, label in enumerate(EMOTION_INDEX):
            if probs[i] < NOISE_FLOOR:
                probs[i] = 0.0
            if label in EMOTION_DAMPENING:
                probs[i] *= EMOTION_DAMPENING[label]
        total = probs.sum()
        if total > 0:
            probs /= total

        emotion_dict = {
            EMOTION_INDEX[i]: round(float(probs[i]), 4)
            for i in range(len(EMOTION_INDEX))
        }

        gaze_vals = gaze_output[0].detach().cpu().numpy()
        gaze = {
            "yaw":   float(gaze_vals[0]),
            "pitch": float(gaze_vals[1]),
        }

        au_vals = au_output[0].detach().cpu().numpy()
        au_dict = {
            AU_NAMES[i]: round(float(au_vals[i]), 4)
            for i in range(min(len(AU_NAMES), len(au_vals)))
        }

        return {
            "emotion":         emotion_dict,
            "gaze":            gaze,
            "action_units":    au_dict,
            "_det_confidence": float(dets[0][-1]) if len(dets) > 0 else 0.0,
        }

    except Exception as e:
        print(f"[Video] Frame analysis failed: {e}")
        return None
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)