import librosa
import numpy as np


def extract_features(audio_path: str):
    """
    Extract comprehensive audio features for analysis.
    Includes raw features plus HR-relevant metrics.
    """
    y, sr = librosa.load(audio_path, sr=16000)

    # --- Basic timing ---
    duration = librosa.get_duration(y=y, sr=sr)
    intervals = librosa.effects.split(y, top_db=25)
    speech_duration = sum((end - start) for start, end in intervals) / sr
    speech_ratio = speech_duration / duration if duration else 0
    
    # --- Energy (RMS) ---
    rms = librosa.feature.rms(y=y)[0]
    rms_mean = float(np.mean(rms))
    rms_std = float(np.std(rms))
    
    # --- Pitch analysis ---
    pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
    pitch_vals = pitches[magnitudes > np.median(magnitudes)]
    pitch_std = float(np.std(pitch_vals)) if len(pitch_vals) else 0
    pitch_mean = float(np.mean(pitch_vals)) if len(pitch_vals) else 0
    
    # --- Pause detection and analysis ---
    pause_durations = []
    long_pause_count = 0
    for i in range(len(intervals) - 1):
        pause_duration = (intervals[i + 1][0] - intervals[i][1]) / sr
        pause_durations.append(pause_duration)
        if pause_duration > 2.0:  # Long pause threshold: 2 seconds
            long_pause_count += 1
    
    avg_pause = float(np.mean(pause_durations)) if pause_durations else 0.0
    max_pause = float(np.max(pause_durations)) if pause_durations else 0.0
    
    # --- Speech rate consistency (comparing early vs late) ---
    mid_point = len(intervals) // 2
    if mid_point > 0:
        early_intervals = intervals[:mid_point]
        late_intervals = intervals[mid_point:]
        
        early_duration = sum((end - start) for start, end in early_intervals) / sr
        late_duration = sum((end - start) for start, end in late_intervals) / sr
        
        # Normalize to how well they split the available time
        expected_per_half = speech_duration / 2 if speech_duration > 0 else 1
        early_ratio = early_duration / expected_per_half if expected_per_half > 0 else 0.5
        late_ratio = late_duration / expected_per_half if expected_per_half > 0 else 0.5
        
        # How consistent is the rate (closer to 1.0 = perfectly even)
        rate_consistency = 100 * (1.0 - abs(early_ratio - late_ratio) / 2.0)
        rate_consistency = max(0.0, min(100.0, rate_consistency))
    else:
        rate_consistency = 50.0
    
    # --- MFCCs for speech quality ---
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    mfcc_mean = np.mean(mfcc, axis=1).tolist()
    
    # --- Delta MFCCs (speech dynamics/smoothness) ---
    delta_mfcc = librosa.feature.delta(mfcc)
    delta_std = float(np.std(delta_mfcc))
    
    # Normalize to 0-100 (higher = smoother speech)
    mfcc_smoothness = min(100.0, max(0.0, 100.0 / (1.0 + delta_std)))
    
    # --- Signal-to-noise ratio estimation ---
    # Use ratio of speech energy to overall energy
    speech_energy = np.sum(rms[rms > np.percentile(rms, 25)])
    noise_energy = np.sum(rms[rms <= np.percentile(rms, 25)])
    snr_estimate = 10 * np.log10((speech_energy / len(rms)) / (noise_energy / len(rms) + 1e-9))
    snr_estimate = float(snr_estimate)
    
    return {
        # Timing & speech ratio
        "duration": duration,
        "speech_duration": speech_duration,
        "speech_ratio": speech_ratio,
        
        # Energy metrics
        "rms_mean": rms_mean,
        "rms_std": rms_std,
        
        # Pitch metrics
        "pitch_std": pitch_std,
        "pitch_mean": pitch_mean,
        
        # Pause metrics (HR relevant)
        "avg_pause_sec": avg_pause,
        "max_pause_sec": max_pause,
        "long_pause_count": long_pause_count,
        
        # Speech rate consistency (HR relevant)
        "speech_rate_consistency": rate_consistency,  # 0-100
        
        # Speech quality metrics
        "mfcc_mean": mfcc_mean,
        "mfcc_smoothness": mfcc_smoothness,  # 0-100 (higher = smoother)
        
        # Audio environment
        "snr_estimate_db": snr_estimate,
    }