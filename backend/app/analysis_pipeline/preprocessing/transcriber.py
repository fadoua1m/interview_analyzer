import os
import re
from pathlib import Path

from groq import Groq
from app.config import settings
from app.analysis_pipeline.preprocessing.audio_extractor import extract_audio

_client = Groq(api_key=settings.groq_api_key)
MODEL   = "whisper-large-v3-turbo"


# ── Cleaning ──────────────────────────────────────────────────────────────────

def _remove_timestamps(text: str) -> str:
    return re.sub(r'\b\d{1,2}:\d{2}(?::\d{2})?\b', '', text)


def _remove_fillers(text: str) -> str:
    pattern = r'\b(um|uh|uhh|er|ah|you know|so uh|uh so|i mean)\b'
    return re.sub(pattern, '', text, flags=re.IGNORECASE)


def _remove_repetitions(text: str) -> str:
    # removes immediately repeated phrases e.g. "donation camps donation camps"
    return re.sub(r'\b(.{10,}?)\s+\1\b', r'\1', text, flags=re.IGNORECASE)


def _extract_candidate_speech(text: str) -> str:
    """
    Splits off interviewer speech that appears after the candidate's answer.
    Only splits if candidate speech is already substantial (>300 chars).
    """
    cues = [
        r'\bokay\s+um\b', r'\bokay\s+so\b', r'\balright\b',
        r'\bwhat are the\b', r'\bcan you tell\b', r'\bcould you\b',
        r'\bwhy do you\b', r'\bhow do you\b', r'\bnext question\b',
    ]
    match = re.search('|'.join(cues), text, flags=re.IGNORECASE)
    if match and match.start() > 300:
        return text[:match.start()].strip()
    return text


def clean_transcript(raw: str) -> str:
    text = _remove_timestamps(raw)
    text = _extract_candidate_speech(text)
    text = _remove_fillers(text)
    text = _remove_repetitions(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# ── Main ──────────────────────────────────────────────────────────────────────

def transcribe(video_path: str) -> dict:
    """
    Transcribes video using Groq Whisper.
    Returns:
        text:       raw Whisper output — kept for audit
        clean_text: candidate-only cleaned text — used by all analysis modules
        segments:   list of {start, end, text}
    """
    audio_path, is_temp = extract_audio(video_path)

    try:
        with open(audio_path, "rb") as f:
            response = _client.audio.transcriptions.create(
                file=           (Path(audio_path).name, f),
                model=          MODEL,
                response_format="verbose_json",
                language=       "en",
                temperature=    0.0,
            )
    except Exception:
        if is_temp:
            try:
                os.unlink(audio_path)
            except OSError:
                pass
        raise

    raw_text   = response.text
    clean_text = clean_transcript(raw_text)

    print(f"[Transcribe] raw:   {len(raw_text)} chars")
    print(f"[Transcribe] clean: {len(clean_text)} chars")

    return {
        "text":       raw_text,
        "clean_text": clean_text,
        "segments": [
            {"start": seg["start"], "end": seg["end"], "text": seg["text"]}
            for seg in (response.segments or [])
        ],
        "audio_path": audio_path,
        "audio_is_temp": is_temp,

    }