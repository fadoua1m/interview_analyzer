def compute_completeness(text: str, expected_words: int = 120):
    wc = len(text.split())
    ratio = wc / expected_words

    return {
        "score": round(min(100, ratio * 100), 2),
        "word_count": wc,
    }