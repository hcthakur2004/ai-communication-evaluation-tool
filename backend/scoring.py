import math
from typing import Dict, Any, List, Optional
import numpy as np
from .rubric_loader import load_rubric

# Lazy import; actual model created in main.py and passed in


def _tokenize(text: str) -> List[str]:
    return text.lower().split()


def _word_count(text: str) -> int:
    return len(_tokenize(text))


def _keyword_presence_score(transcript: str, keywords: List[str]) -> Dict[str, Any]:
    """Compute keyword presence score between 0 and 1 and list of hits."""
    text_lower = transcript.lower()
    hits = []
    for kw in keywords:
        if kw and kw in text_lower:
            hits.append(kw)
    total = len(keywords)
    score = (len(hits) / total) if total > 0 else 0.0
    return {"score": score, "hits": hits, "total_keywords": total}


def _length_factor(words: int, min_words: Optional[float], max_words: Optional[float]) -> Dict[str, Any]:
    """Return a factor in [0.6, 1.0] to softly penalize being out of bounds and feedback."""
    factor = 1.0
    feedback = "Within suggested length."
    if min_words and not math.isnan(min_words):
        if words < min_words:
            # soft penalty proportional to deficit capped
            deficit = min_words - words
            factor *= max(0.6, 1.0 - (deficit / max(min_words, 1)) * 0.5)
            feedback = f"Below min words ({words} < {int(min_words)}). Consider adding detail."
    if max_words and not math.isnan(max_words):
        if words > max_words:
            excess = words - max_words
            factor *= max(0.6, 1.0 - (excess / max(max_words, 1)) * 0.5)
            feedback = f"Above max words ({words} > {int(max_words)}). Consider tightening."
    return {"factor": max(0.6, min(1.0, factor)), "feedback": feedback}


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def score_transcript(transcript: str, rubric_df, model=None) -> Dict[str, Any]:
    words = _word_count(transcript)
    results = []

    # Prepare embedding for transcript once
    transcript_vec = None
    if model is not None:
        transcript_vec = np.array(model.encode([transcript])[0])

    for _, row in rubric_df.iterrows():
        criterion = str(row.get("criterion", "Criterion")).strip()
        description = str(row.get("description", "")).strip()
        keywords = row.get("keywords_list", []) or []
        weight = float(row.get("norm_weight", 0.0))
        min_words = row.get("min_words", np.nan)
        max_words = row.get("max_words", np.nan)

        # Rule-based
        kw_res = _keyword_presence_score(transcript, keywords)
        kw_score = kw_res["score"]  # 0..1

        # Semantic
        sem_score = 0.0
        if model is not None and description:
            desc_vec = np.array(model.encode([description])[0])
            sem_score = _cosine_similarity(transcript_vec, desc_vec)  # -1..1
            sem_score = max(0.0, sem_score)  # clamp to 0..1 (ignore negatives)

        # Length factor
        len_res = _length_factor(words, min_words, max_words)
        length_factor = len_res["factor"]

        # Combine signals for per-criterion score
        # If keywords exist, give them more weight; otherwise semantic dominates
        if len(keywords) > 0:
            w_keywords = 0.6
            w_semantic = 0.4
        else:
            w_keywords = 0.3
            w_semantic = 0.7

        base_score = w_keywords * kw_score + w_semantic * sem_score  # 0..1
        per_criterion_score = max(0.0, min(1.0, base_score)) * length_factor
        per_criterion_score_pct = round(per_criterion_score * 100, 2)

        # Feedback
        feedback_parts = []
        if len(keywords) > 0:
            if kw_res["hits"]:
                feedback_parts.append(f"Keywords found: {', '.join(kw_res['hits'])}")
            else:
                feedback_parts.append("No rubric keywords detected; consider including key terms.")
        if description:
            feedback_parts.append(f"Semantic similarity: {round(sem_score, 3)}")
        feedback_parts.append(len_res["feedback"])

        results.append({
            "criterion": criterion,
            "description": description,
            "keywords": keywords,
            "weight": weight,
            "words": words,
            "score": per_criterion_score_pct,
            "semantic_similarity": round(sem_score, 3),
            "keyword_hits": kw_res["hits"],
            "feedback": "; ".join(feedback_parts),
        })

    # Overall score: weighted average
    overall = 0.0
    for r in results:
        overall += r["score"] * r["weight"]
    overall = round(overall, 2)

    return {
        "overall_score": overall,
        "words": words,
        "criteria": results,
    }