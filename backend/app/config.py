# app/config.py
from pydantic_settings import BaseSettings
from typing import Dict, List
import json


class Settings(BaseSettings):
    supabase_url:         str
    supabase_service_key: str
    gemini_api_key:       str
    groq_api_key:         str
    openface_weights_dir: str
    app_env:              str = "development"
    cors_origins:         str = "http://localhost:5173"

    gemini_model:                    str = "gemini-2.5-flash"
    gemini_temperature:              float = 0.0
    gemini_max_retries:              int = 3
    gemini_retry_base_delay_sec:     float = 0.6

    whisper_model:                   str = "whisper-large-v3-turbo"
    whisper_language:                str = "auto"

    segment_max_transcript_chars:    int = 18000
    segment_llm_attempts:            int = 2
    segment_no_answer_placeholder:   str = "[No answer extracted]"

    text_min_answer_words:           int = 6
    text_relevance_max_workers:      int = 5
    soft_skills_max_transcript_chars:int = 8000

    transcript_split_min_chars:      int = 300
    transcript_fillers:              str = "um,uh,uhh,er,ah,you know,so uh,uh so,i mean,euh,ben,alors"
    transcript_interviewer_cues:     str = "okay um,okay so,alright,what are the,can you tell,could you,why do you,how do you,next question,d accord,alors,pouvez vous,peux tu,parlez moi,prochaine question"

    text_embedder_model:             str = "sentence-transformers/all-MiniLM-L6-v2"
    text_nli_model:                  str = "cross-encoder/nli-deberta-v3-small"
    text_fuzzy_threshold:            float = 0.85
    text_semantic_threshold:         float = 0.75
    text_nli_threshold:              float = 0.35
    text_nli_hard_drop_threshold:    float = 0.20

    video_frame_fps_target:          int = 1
    video_min_high_quality_frames:   int = 10
    video_face_detect_reliable_pct:  float = 40.0
    video_quality_confidence_threshold: float = 0.5
    video_gaze_max_deviation:        float = 0.5
    video_emotion_noise_floor:       float = 0.05
    video_emotion_dampening_json:    str = '{"contempt": 0.05, "disgust": 0.10, "anger": 0.30, "fear": 0.40, "surprise": 0.40}'
    video_au_threshold_json:         str = '{"smile_6": 0.05, "smile_12": 0.05, "concern_4": 0.05, "sad_15": 0.05, "sad_17": 0.05, "nervous_1": 0.05, "nervous_2": 0.05}'
    video_score_calibration_json:    str = "{}"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def transcript_fillers_list(self) -> List[str]:
        return [item.strip() for item in self.transcript_fillers.split(",") if item.strip()]

    @property
    def transcript_interviewer_cues_list(self) -> List[str]:
        return [item.strip() for item in self.transcript_interviewer_cues.split(",") if item.strip()]

    @property
    def video_emotion_dampening(self) -> Dict[str, float]:
        try:
            value = json.loads(self.video_emotion_dampening_json)
            return value if isinstance(value, dict) else {}
        except Exception:
            return {}

    @property
    def video_au_thresholds(self) -> Dict[str, float]:
        try:
            value = json.loads(self.video_au_threshold_json)
            return value if isinstance(value, dict) else {}
        except Exception:
            return {}

    @property
    def video_score_calibration(self) -> Dict:
        try:
            value = json.loads(self.video_score_calibration_json)
            return value if isinstance(value, dict) else {}
        except Exception:
            return {}

    class Config:
        env_file = ".env"


settings = Settings()