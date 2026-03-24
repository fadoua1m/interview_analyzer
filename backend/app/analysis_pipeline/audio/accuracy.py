import torch
from app.analysis_pipeline.audio.wav2vec_extractor import extract_embeddings


def compute_accuracy(audio_path: str) -> dict:
    emb = extract_embeddings(audio_path)

    # --- temporal stability ---
    diffs = torch.norm(emb[1:] - emb[:-1], dim=1)
    stability = torch.mean(diffs).item()

    # --- entropy ---
    probs = torch.softmax(emb, dim=-1)
    entropy = -torch.sum(probs * torch.log(probs + 1e-9), dim=-1)
    avg_entropy = torch.mean(entropy).item()

    # normalize (empirical)
    stability_score = max(0, 1 - stability)
    entropy_score = max(0, 1 - avg_entropy / 5)

    score = (0.6 * stability_score + 0.4 * entropy_score) * 100

    return {
        "score": round(score, 2),
        "stability": stability,
        "entropy": avg_entropy,
    }