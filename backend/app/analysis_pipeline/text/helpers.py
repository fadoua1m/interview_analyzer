import json
import re
import difflib
from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer, CrossEncoder, util

from app.constants.competencies import COMPETENCY_BANK


# ── JSON parsing ──────────────────────────────────────────────────────────────

def parse_json(raw: str) -> dict | list:
    """
    Strip markdown code fences from LLM output and parse as JSON.
    Handles trailing newlines after the closing fence.
    """
    text = raw.strip()

    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]

    if text.endswith("```"):
        text = text[:-3]

    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"[parse_json] FAILED: {e}")
        print(f"[parse_json] input was: {raw[:300]}")
        raise


# ── Model loading — once at startup ──────────────────────────────────────────

@lru_cache(maxsize=1)
def load_embedder() -> SentenceTransformer:
    """
    MiniLM — 22MB semantic similarity model.
    Layer 2 verification: checks quote exists in transcript
    even with transcription variants.
    """
    return SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


@lru_cache(maxsize=1)
def load_nli() -> CrossEncoder:
    """
    DeBERTa NLI — 142MB cross-encoder.
    Layer 3 verification: checks quote actually proves the assigned competency.

    predict() output shape: (n_pairs, 3)
    Label order: [contradiction, entailment, neutral]
    Index 1 = entailment logit.
    Apply softmax before comparing to threshold.
    """
    return CrossEncoder("cross-encoder/nli-deberta-v3-small")


# ── Transcript pre-encoding — call once per request, not per skill ────────────

def encode_transcript(transcript: str) -> tuple[list[str], any]:
    """
    Split transcript into sentences and encode all at once.
    Call this ONCE before the verification loop and pass the result in.

    Returns (sentences, embeddings).
    Returns ([], None) on failure — verify_skill handles this gracefully.
    """
    sentences = [
        s.strip()
        for s in re.split(r'[.!?\n]', transcript)
        if len(s.strip()) > 10
    ]

    if not sentences:
        return [], None

    try:
        embeddings = load_embedder().encode(sentences, convert_to_tensor=True)
        return sentences, embeddings
    except Exception as e:
        print(f"[encode_transcript] FAILED: {e} — semantic verification disabled")
        return [], None


# ── Verification layers ───────────────────────────────────────────────────────

def fuzzy_match(quote: str, transcript: str, threshold: float = 0.85) -> bool:
    """
    Layer 1 — fast string-level check.
    Checks exact substring or near character match (typos, punctuation).
    No model required.
    Returns True if found.
    """
    q = quote.lower().strip()
    t = transcript.lower()

    if q in t:
        return True

    words  = t.split()
    qwords = q.split()
    n      = max(len(qwords), 1)

    for i in range(len(words) - n + 1):
        window = " ".join(words[i : i + n])
        if difflib.SequenceMatcher(None, q, window).ratio() >= threshold:
            return True

    return False


def semantic_match(
    quote:      str,
    sentences:  list[str],
    s_embs:     any,
    threshold:  float = 0.75,
) -> tuple[bool, float]:
    """
    Layer 2 — semantic similarity using MiniLM.
    Compares quote against pre-encoded transcript sentences.
    Catches transcription variants where words differ but meaning is the same.

    Accepts pre-encoded sentences from encode_transcript() — do not re-encode here.
    Returns (is_match, best_similarity_score).
    """
    if not sentences or s_embs is None:
        return False, 0.0

    try:
        q_emb = load_embedder().encode(quote, convert_to_tensor=True)
        sims  = util.cos_sim(q_emb, s_embs)[0]
        best  = float(sims.max())
        return best >= threshold, round(best, 3)
    except Exception as e:
        print(f"[semantic_match] FAILED: {e}")
        return False, 0.0


def nli_match(
    quote:          str,
    competency_key: str,
    threshold:      float = 0.35,
) -> tuple[bool, float]:
    """
    Layer 3 — NLI entailment using DeBERTa CrossEncoder.
    Checks: does this quote actually prove this specific competency?

    CrossEncoder.predict() returns raw logits shape (1, 3).
    Label order: [contradiction, entailment, neutral] — index 1 is entailment.
    Softmax applied to convert logits to probabilities before threshold comparison.

    Threshold 0.35 is intentionally low — short spoken quotes produce
    lower entailment scores than written text against long definitions.
    Scores below 0.20 = clearly wrong competency assignment → hard drop.

    Returns (is_match, entailment_probability).
    """
    definition = COMPETENCY_BANK.get(competency_key, "")

    if not definition:
        # not in competency bank — CoT already validated it, let it pass
        return True, 1.0

    try:
        model   = load_nli()
        logits  = model.predict([(quote, definition[:200])])  # shape (1, 3)

        # softmax: convert raw logits to probabilities that sum to 1
        exp     = np.exp(logits[0] - np.max(logits[0]))  # subtract max for numerical stability
        probs   = exp / exp.sum()

        entailment = float(probs[1])  # index 1 = entailment

        return entailment >= threshold, round(entailment, 3)

    except Exception as e:
        print(f"[nli_match] FAILED for '{competency_key}': {e}")
        # on failure let it pass — quote existence already confirmed by L1/L2
        return True, 0.5


# ── Combined verification gate ────────────────────────────────────────────────

def verify_skill(
    item:      dict,
    transcript: str,
    sentences:  list[str],
    s_embs:     any,
) -> bool:
    """
    Three-layer verification gate for a detected soft skill.

    Layer 1 — fuzzy string match     (fast, no model, always runs)
    Layer 2 — MiniLM semantic match  (only runs if Layer 1 fails)
    Layer 3 — DeBERTa NLI entailment (runs once quote is confirmed)

    Accept when:
      - quote found in transcript by fuzzy OR semantic
      - NLI entailment probability >= 0.20

    Logs result of each layer for debugging.
    """
    quote = item.get("quote", "")
    name  = item.get("name", "")

    # layer 1 — fast, no model
    fuzzy_ok = fuzzy_match(quote, transcript)

    if fuzzy_ok:
        # quote confirmed — skip layer 2
        sem_score = 1.0
    else:
        # layer 2 — semantic similarity
        semantic_ok, sem_score = semantic_match(quote, sentences, s_embs)
        if not semantic_ok:
            print(f"[Verify] DROP  '{name}' — not in transcript  sem={sem_score:.2f}")
            return False

    # layer 3 — NLI competency check
    nli_ok, nli_score = nli_match(quote, name)

    if nli_score < 0.20:
        print(f"[Verify] DROP  '{name}' — NLI={nli_score:.2f} wrong competency")
        return False

    status = "OK  " if nli_ok else "WARN"
    print(f"[Verify] {status} '{name}' — fuzzy={fuzzy_ok} sem={sem_score:.2f} nli={nli_score:.2f}")
    return True