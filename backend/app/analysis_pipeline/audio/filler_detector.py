"""Language-aware filler detection for English/French transcripts."""
import re
from typing import Dict


FILLER_WORDS_EN = {
    "um": 1.0,
    "uh": 1.0,
    "umm": 1.0,
    "uhh": 1.0,
    "like": 0.8,  # lower weight, context-dependent
    "you know": 0.9,
    "i mean": 0.7,
    "sort of": 0.6,
    "kind of": 0.6,
    "basically": 0.5,
    "literally": 0.5,
    "honestly": 0.4,
    "actually": 0.4,
    "well": 0.3,  # contextual, often used naturally
    "so": 0.2,    # too common, requires context
    "just": 0.3,
    "right": 0.2,
    "you know what": 0.9,
    "anyway": 0.3,
    "i guess": 0.6,
}


FILLER_WORDS_FR = {
    "euh": 1.0,
    "ben": 0.7,
    "bah": 0.7,
    "du coup": 0.9,
    "en fait": 0.8,
    "genre": 0.8,
    "tu vois": 0.7,
    "quoi": 0.5,
    "alors": 0.4,
    "donc": 0.4,
    "en gros": 0.7,
    "je veux dire": 0.7,
    "comment dire": 0.8,
    "enfin": 0.5,
}


def detect_language(text: str, hint: str | None = None) -> str:
    if hint and hint.lower() in {"en", "fr"}:
        return hint.lower()
    normalized = (text or "").lower()
    if not normalized.strip():
        return "en"

    fr_markers = [
        " le ", " la ", " les ", " de ", " des ", " et ", " est ", " je ", " vous ", " nous ",
        " pas ", " pour ", " avec ", " une ", " un ", " du ", " en fait", " du coup",
    ]
    en_markers = [
        " the ", " and ", " is ", " are ", " i ", " you ", " we ", " not ", " for ", " with ",
        " a ", " an ", " in fact", " you know",
    ]

    fr_score = sum(normalized.count(marker) for marker in fr_markers)
    en_score = sum(normalized.count(marker) for marker in en_markers)
    return "fr" if fr_score > en_score else "en"


def _get_filler_map(language: str) -> Dict[str, float]:
    return FILLER_WORDS_FR if language == "fr" else FILLER_WORDS_EN


def detect_fillers(transcript: str, language: str = "en") -> Dict:
    """
    Analyze filler words in transcript.
    
    Args:
        transcript: Cleaned transcribed text
        
    Returns:
        {
            "filler_count": int (total fillers detected),
            "filler_percentage": float (% of words),
            "filler_types": {"um": 3, "uh": 1, "like": 5},
            "confidence_score": float (0-100, inverse of filler density),
        }
    """
    if not transcript or len(transcript.strip()) == 0:
        return {
            "filler_count": 0,
            "filler_percentage": 0.0,
            "filler_types": {},
            "confidence_score": 50.0,  # neutral if no transcript
        }
    
    # Normalize: lowercase for matching
    normalized = transcript.lower()
    words = normalized.split()
    total_words = len(words)
    
    if total_words == 0:
        return {
            "filler_count": 0,
            "filler_percentage": 0.0,
            "filler_types": {},
            "confidence_score": 50.0,
        }
    
    # Track multi-word fillers first (greedy match)
    filler_count = 0
    filler_types: Dict[str, int] = {}
    remaining_text = normalized
    
    # Sort by length (longest first) to match multi-word fillers first
    filler_map = _get_filler_map(language)
    sorted_fillers = sorted(filler_map.keys(), key=len, reverse=True)
    
    for filler in sorted_fillers:
        # Use word boundaries to match whole words only
        pattern = r'\b' + re.escape(filler) + r'\b'
        occurrences = len(re.findall(pattern, remaining_text))
        
        if occurrences > 0:
            filler_count += occurrences
            filler_types[filler] = occurrences
            # Remove matched fillers to avoid double-counting
            remaining_text = re.sub(pattern, '', remaining_text)
    
    filler_percentage = (filler_count / total_words) * 100.0 if total_words > 0 else 0.0
    
    # Confidence score: inverse of filler density
    # 0-2% fillers = 90-100 (very confident)
    # 2-5% fillers = 70-90 (confident)
    # 5-10% fillers = 50-70 (moderate)
    # 10-15% fillers = 30-50 (nervous)
    # >15% fillers = 0-30 (very nervous)
    if filler_percentage <= 2.0:
        confidence_score = 95.0
    elif filler_percentage <= 5.0:
        confidence_score = 85.0 - (filler_percentage - 2.0) * 3.33
    elif filler_percentage <= 10.0:
        confidence_score = 70.0 - (filler_percentage - 5.0) * 4.0
    elif filler_percentage <= 15.0:
        confidence_score = 50.0 - (filler_percentage - 10.0) * 4.0
    else:
        confidence_score = max(0.0, 30.0 - (filler_percentage - 15.0) * 2.0)
    
    return {
        "filler_count": filler_count,
        "filler_percentage": round(filler_percentage, 2),
        "filler_types": filler_types,
        "confidence_score": round(confidence_score, 1),
    }


def get_filler_summary(filler_analysis: Dict) -> str:
    """
    Human-readable summary of filler word usage.
    """
    pct = filler_analysis.get("filler_percentage", 0.0)
    count = filler_analysis.get("filler_count", 0)
    
    if pct < 2:
        return f"Minimal fillers ({count} detected, {pct}% of speech) - excellent confidence"
    elif pct < 5:
        return f"Few fillers ({count} detected, {pct}% of speech) - good confidence"
    elif pct < 10:
        return f"Moderate fillers ({count} detected, {pct}% of speech) - some nervousness"
    elif pct < 15:
        return f"Many fillers ({count} detected, {pct}% of speech) - high nervousness"
    else:
        return f"Excessive fillers ({count} detected, {pct}% of speech) - significant anxiety"
