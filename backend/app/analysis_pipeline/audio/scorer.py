def aggregate(fluency, prosody, accuracy, completeness):
    overall = (
        0.3 * fluency["score"] +
        0.2 * prosody["score"] +
        0.3 * accuracy["score"] +
        0.2 * completeness["score"]
    )

    return {
        "fluency": fluency,
        "prosody": prosody,
        "accuracy": accuracy,
        "completeness": completeness,
        "overall": round(overall, 2),
    }