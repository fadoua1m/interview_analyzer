import cv2
import numpy as np
import tempfile
import os
from functools import lru_cache
from pathlib import Path

from app.config import settings


@lru_cache(maxsize=1)
def _load_models():
    from openface.face_detection  import FaceDetector
    from openface.multitask_model import MultitaskPredictor

    weights = Path(settings.openface_weights_dir)

    detector  = FaceDetector(
        model_path=str(weights / "Alignment_RetinaFace.pth"),
        device="cpu",
        vis_threshold=0.5,
    )
    predictor = MultitaskPredictor(
        model_path=str(weights / "MTL_backbone.pth"),
        device="cpu",
    )
    return detector, predictor


def analyse_frame(frame: np.ndarray) -> dict | None:
    """
    Run face detection + multitask prediction on one frame.
    Uses a temp file because OpenFace 3.0 get_face() accepts file paths.
    Returns raw predictions dict or None if no face detected.
    """
    try:
        detector, predictor = _load_models()
    except Exception as e:
        print(f"[Video] Models not loaded: {e}")
        return None

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp_path = tmp.name
            cv2.imwrite(tmp_path, frame)

        cropped_face, dets = detector.get_face(tmp_path)

        if cropped_face is None or dets is None:
            return None

        predictions = predictor.predict(cropped_face)

        # attach detection confidence from dets for quality filtering
        # dets shape: (n_faces, 5) — last col is confidence
        if dets is not None and len(dets) > 0:
            predictions["_det_confidence"] = float(dets[0][-1])
        else:
            predictions["_det_confidence"] = 0.0

        return predictions

    except Exception as e:
        print(f"[Video] Frame analysis failed: {e}")
        return None
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)