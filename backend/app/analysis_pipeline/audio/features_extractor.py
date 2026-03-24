import librosa
import numpy as np


def extract_features(audio_path: str):
    y, sr = librosa.load(audio_path, sr=16000)

    duration = librosa.get_duration(y=y, sr=sr)

    intervals = librosa.effects.split(y, top_db=25)
    speech_duration = sum((end - start) for start, end in intervals) / sr

    rms = librosa.feature.rms(y=y)[0]

    pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
    pitch_vals = pitches[magnitudes > np.median(magnitudes)]

    return {
        "duration": duration,
        "speech_duration": speech_duration,
        "speech_ratio": speech_duration / duration if duration else 0,
        "rms_mean": float(np.mean(rms)),
        "rms_std": float(np.std(rms)),
        "pitch_std": float(np.std(pitch_vals)) if len(pitch_vals) else 0,
    }