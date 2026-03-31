def aggregate(fluency, prosody, completeness):
    overall = (
        0.45 * fluency["score"] +
        0.25 * prosody["score"] +
        0.30 * completeness["score"]
    )

    return {
        "fluency": fluency,
        "prosody": prosody,
        "completeness": completeness,
        "overall": round(overall, 2),
    }