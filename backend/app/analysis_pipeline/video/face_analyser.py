import sys
import cv2
import numpy as np
import tempfile
import os
import torch
from functools import lru_cache
from pathlib import Path

from app.config import settings


@lru_cache(maxsize=1)
def _load_models():
    video_dir = Path(__file__).resolve().parent
    weights = video_dir / "weights"

    original_argv = sys.argv[:]
    original_cwd = Path.cwd()
    try:
        sys.argv = [sys.argv[0]]
        os.chdir(video_dir)

        from openface.face_detection import FaceDetector
        from openface.multitask_model import MultitaskPredictor

        detector = FaceDetector(
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


EMOTION_INDEX = [
    "neutral", "happiness", "sadness",
    "surprise", "fear", "disgust", "anger", "contempt"
]

# Output order from the multitask model
AU_NAMES = [
    "AU01", "AU02", "AU04", "AU05", "AU06", "AU07",
    "AU09", "AU10", "AU12", "AU14", "AU15", "AU17",
    "AU20", "AU23", "AU25", "AU26", "AU28", "AU45"
]

#
EMOTION_NOISE_DAMPENING = {
    "contempt": 0.3,   
    "disgust":  0.4,   
    "anger":    0.6,  
    "fear":     0.7,
}


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

        # Emotion — softmax probabilities, then dampen noise-prone labels
        probs_raw = torch.softmax(emotion_logits, dim=1)[0]
        probs     = probs_raw.detach().cpu().numpy().copy()

        for i, label in enumerate(EMOTION_INDEX):
            if label in EMOTION_NOISE_DAMPENING:
                probs[i] *= EMOTION_NOISE_DAMPENING[label]

        # Re-normalise after dampening
        probs = probs / probs.sum()

        emotion_dict = {
            EMOTION_INDEX[i]: round(float(probs[i]), 4)
            for i in range(len(EMOTION_INDEX))
        }
        dominant = EMOTION_INDEX[int(np.argmax(probs))]

        # Gaze — model outputs [yaw, pitch] as a single prediction
        gaze_vals = gaze_output[0].detach().cpu().numpy()
        yaw   = float(gaze_vals[0])
        pitch = float(gaze_vals[1])
        gaze  = {
            "left":  {"yaw": yaw, "pitch": pitch},
            "right": {"yaw": yaw, "pitch": pitch},
        }

        # Action Units — model outputs values in [0, 1] range
        # AU_NAMES are already zero-padded (AU06, AU12 etc.) to match aggregator
        au_vals = au_output[0].detach().cpu().numpy()
        au_dict = {
            AU_NAMES[i]: round(float(au_vals[i]), 4)
            for i in range(min(len(AU_NAMES), len(au_vals)))
        }

        det_confidence = float(dets[0][-1]) if len(dets) > 0 else 0.0
        
        return {
            "emotion":         emotion_dict,
            "dominant_emotion": dominant,
            "gaze":            gaze,
            "action_units":    au_dict,
            "_det_confidence": det_confidence,
        }

    except Exception as e:
        print(f"[Video] Frame analysis failed: {e}")
        return None
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)