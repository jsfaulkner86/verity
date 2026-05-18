"""Per-dimension scoring heuristics.

Each scorer is a pure function from inputs -> DimensionScore. They are
intentionally simple, deterministic, and side-effect free. The product
direction is to swap individual heuristics for stronger
model-backed scorers behind these same signatures.
"""

from __future__ import annotations

import math
import re
from collections.abc import Sequence

from verity.core.schemas import Claim, ClaimType, Dimension, DimensionScore

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return {tok for tok in _TOKEN_RE.findall(text.lower()) if len(tok) > 2}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def score_source_grounding(response_text: str, sources: Sequence[str]) -> DimensionScore:
    """How well does the response overlap with provided retrieval context?

    When no sources are supplied, the dimension is reported as 0.5 (neutral)
    rather than 0.0 — absence of evidence is not evidence of ungrounding.
    """
    if not sources:
        return DimensionScore(
            dimension=Dimension.SOURCE_GROUNDING,
            score=0.5,
            rationale="No sources supplied; grounding is neutral.",
            evidence_count=0,
        )
    response_toks = _tokens(response_text)
    source_toks = _tokens(" ".join(sources))
    overlap = _jaccard(response_toks, source_toks)
    # Smooth so that small response/source pairs aren't punished too hard.
    score = round(min(1.0, overlap * 1.5), 4)
    return DimensionScore(
        dimension=Dimension.SOURCE_GROUNDING,
        score=score,
        rationale=f"Token-overlap (Jaccard) with {len(sources)} source(s): {overlap:.2f}.",
        evidence_count=len(sources),
    )


def score_factual_consistency(claims: Sequence[Claim], sources: Sequence[str]) -> DimensionScore:
    """Fraction of factual/numeric/citation claims supported by sources.

    Without sources, falls back to a self-consistency proxy: penalizes
    contradictory hedged + assertive pairs and unsupported numerics.
    """
    factual_claims = [
        c
        for c in claims
        if c.type in {ClaimType.FACTUAL, ClaimType.NUMERIC, ClaimType.CITATION, ClaimType.CLINICAL}
    ]
    if not factual_claims:
        return DimensionScore(
            dimension=Dimension.FACTUAL_CONSISTENCY,
            score=0.7,
            rationale="No verifiable claims detected.",
            evidence_count=0,
        )

    if sources:
        source_toks = _tokens(" ".join(sources))
        supported = 0
        for c in factual_claims:
            if _jaccard(_tokens(c.text), source_toks) >= 0.15:
                supported += 1
        ratio = supported / len(factual_claims)
        return DimensionScore(
            dimension=Dimension.FACTUAL_CONSISTENCY,
            score=round(ratio, 4),
            rationale=(f"{supported}/{len(factual_claims)} verifiable claims have source overlap."),
            evidence_count=supported,
        )

    # No sources — penalize ungrounded numerics; reward hedged uncertainty.
    numerics = [c for c in factual_claims if c.type == ClaimType.NUMERIC]
    unsupported_numeric_penalty = 0.1 * len(numerics)
    base = 0.65
    score = max(0.0, base - unsupported_numeric_penalty)
    return DimensionScore(
        dimension=Dimension.FACTUAL_CONSISTENCY,
        score=round(score, 4),
        rationale=(f"No sources; {len(numerics)} ungrounded numeric claim(s) penalized."),
        evidence_count=0,
    )


def score_claim_specificity(claims: Sequence[Claim]) -> DimensionScore:
    """High-specificity claims (numeric, clinical, citation) raise risk.

    The score is the *calibration* of specificity: a response full of
    high-specificity claims without hedging scores LOW (risky), while a
    mix or appropriately-hedged specifics scores high.
    """
    if not claims:
        return DimensionScore(
            dimension=Dimension.CLAIM_SPECIFICITY,
            score=0.5,
            rationale="No claims detected.",
            evidence_count=0,
        )

    high_risk_types = {ClaimType.NUMERIC, ClaimType.CLINICAL, ClaimType.CITATION}
    high_risk = [c for c in claims if c.type in high_risk_types]
    if not high_risk:
        return DimensionScore(
            dimension=Dimension.CLAIM_SPECIFICITY,
            score=0.85,
            rationale="No high-specificity claims; low precision risk.",
            evidence_count=0,
        )

    hedged_ratio = sum(1 for c in high_risk if c.hedged) / len(high_risk)
    density = len(high_risk) / len(claims)
    # Heavy density + zero hedging => low score. Hedging recovers it.
    score = 1.0 - (density * 0.6) + (hedged_ratio * 0.3)
    score = max(0.0, min(1.0, score))
    return DimensionScore(
        dimension=Dimension.CLAIM_SPECIFICITY,
        score=round(score, 4),
        rationale=(
            f"{len(high_risk)} high-specificity claim(s); "
            f"hedged_ratio={hedged_ratio:.2f}, density={density:.2f}."
        ),
        evidence_count=len(high_risk),
    )


def score_hedging_calibration(claims: Sequence[Claim]) -> DimensionScore:
    """Calibration of hedging language to claim risk.

    Best score: high-risk claims are hedged, low-risk claims are not.
    Worst score: high-risk claims unhedged OR low-risk claims drowning
    in hedges.
    """
    if not claims:
        return DimensionScore(
            dimension=Dimension.HEDGING_CALIBRATION,
            score=0.5,
            rationale="No claims to calibrate against.",
            evidence_count=0,
        )

    high_risk_types = {ClaimType.NUMERIC, ClaimType.CLINICAL, ClaimType.CITATION}
    high = [c for c in claims if c.type in high_risk_types]
    low = [c for c in claims if c.type not in high_risk_types]

    high_hedged = sum(1 for c in high if c.hedged) / len(high) if high else 1.0
    low_unhedged = sum(1 for c in low if not c.hedged) / len(low) if low else 1.0

    score = 0.5 * high_hedged + 0.5 * low_unhedged
    # Sigmoid-style smoothing to avoid pegging at 0 or 1.
    score = round(1 / (1 + math.exp(-6 * (score - 0.5))), 4)
    return DimensionScore(
        dimension=Dimension.HEDGING_CALIBRATION,
        score=score,
        rationale=(f"high_hedged_ratio={high_hedged:.2f}, low_unhedged_ratio={low_unhedged:.2f}."),
        evidence_count=len(high),
    )
