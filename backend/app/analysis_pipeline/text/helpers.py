import json
import re
import difflib
from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer, CrossEncoder, util


# ── JSON parsing ──────────────────────────────────────────────────────────────

def parse_json(raw: str) -> dict | list:
    """
    Strip markdown code fences from LLM output and parse as JSON.
    Handles trailing newlines after the closing fence.
    """
    text = (raw or "").strip()

    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, flags=re.IGNORECASE)
    if fenced:
        text = fenced.group(1).strip()

    candidates = [text]

    obj_start = text.find("{")
    obj_end = text.rfind("}")
    if obj_start != -1 and obj_end != -1 and obj_end > obj_start:
        candidates.append(text[obj_start:obj_end + 1].strip())

    arr_start = text.find("[")
    arr_end = text.rfind("]")
    if arr_start != -1 and arr_end != -1 and arr_end > arr_start:
        candidates.append(text[arr_start:arr_end + 1].strip())

    for candidate in candidates:
        if not candidate:
            continue
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    print("[parse_json] FAILED: unable to extract valid JSON")
    print(f"[parse_json] input was: {raw[:300]}")
    raise json.JSONDecodeError("Unable to parse JSON from model output", text, 0)


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
    DeBERTa NLI cross-encoder used for competency entailment checks.
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
    quote: str,
    competency_key: str,
    threshold: float = 0.35,
    competency_bank: dict[str, str] | None = None,
) -> tuple[bool, float]:
    """
    Layer 3 — NLI entailment using DeBERTa CrossEncoder.
    Checks whether the quote supports the assigned competency definition.

    Returns (is_match, entailment_probability).
    """
    source_bank = competency_bank or {}
    definition = source_bank.get(competency_key, "")

    if not definition:
        return True, 1.0

    try:
        model = load_nli()
        logits = model.predict([(quote, definition[:200])])

        exp = np.exp(logits[0] - np.max(logits[0]))
        probs = exp / exp.sum()

        entailment_idx = 1
        try:
            label2id = getattr(model.model.config, "label2id", {}) or {}
            for label, idx in label2id.items():
                if "entail" in str(label).lower():
                    entailment_idx = int(idx)
                    break
        except Exception:
            pass

        if entailment_idx < 0 or entailment_idx >= len(probs):
            entailment_idx = 1

        entailment = float(probs[entailment_idx])

        return entailment >= threshold, round(entailment, 3)

    except Exception as e:
        print(f"[nli_match] FAILED for '{competency_key}': {e}")
        return True, 0.5


# ── Combined verification gate ────────────────────────────────────────────────

def verify_skill(
    item: dict,
    transcript: str,
    sentences: list[str],
    s_embs: any,
    competency_bank: dict[str, str] | None = None,
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

    nli_ok, nli_score = nli_match(quote, name, competency_bank=competency_bank)
    if nli_score < 0.20:
        print(f"[Verify] DROP  '{name}' — NLI={nli_score:.2f} wrong competency")
        return False

    status = "OK  " if nli_ok else "WARN"
    print(f"[Verify] {status} '{name}' — fuzzy={fuzzy_ok} sem={sem_score:.2f} nli={nli_score:.2f}")
    return True