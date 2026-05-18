"""Scoring engine entry point.

Combines per-dimension scores into a composite scorecard and routes
through the HITL decision module. Pure and deterministic; safe to call
from sync or async contexts.
"""

from __future__ import annotations

from verity.claims import extract_claims
from verity.config import Settings, get_settings
from verity.core.schemas import (
    DimensionScore,
    ScorecardResult,
    ScoreRequest,
)
from verity.hitl.router import decide
from verity.observability.phi import detect_phi
from verity.scoring.dimensions import (
    score_claim_specificity,
    score_factual_consistency,
    score_hedging_calibration,
    score_source_grounding,
)

# Composite weights — tuned for clinical-leaning defaults. Source
# grounding and factual consistency dominate; specificity and hedging
# calibrate the bottom of the range.
_DIMENSION_WEIGHTS: dict[str, float] = {
    "source_grounding": 0.35,
    "factual_consistency": 0.35,
    "claim_specificity": 0.15,
    "hedging_calibration": 0.15,
}


def _composite(scores: list[DimensionScore]) -> float:
    total = 0.0
    weight_sum = 0.0
    for s in scores:
        w = _DIMENSION_WEIGHTS.get(s.dimension.value, 0.0)
        total += w * s.score
        weight_sum += w
    return round(total / weight_sum if weight_sum else 0.0, 4)


def score_response(request: ScoreRequest, settings: Settings | None = None) -> ScorecardResult:
    """Score an LLM response across four dimensions and return the full scorecard."""
    cfg = settings or get_settings()

    claims = extract_claims(request.response_text)

    dim_scores: list[DimensionScore] = [
        score_source_grounding(request.response_text, request.sources),
        score_factual_consistency(claims, request.sources),
        score_claim_specificity(claims),
        score_hedging_calibration(claims),
    ]

    overall = _composite(dim_scores)
    phi_flagged = detect_phi(request.response_text) if cfg.phi_detection else False

    hitl = decide(
        overall_score=overall,
        dimensions=dim_scores,
        claims=claims,
        phi_flagged=phi_flagged,
        domain=request.domain,
        settings=cfg,
    )

    return ScorecardResult(
        request_id=request.request_id,
        source_model=request.source_model,
        domain=request.domain,
        overall_score=overall,
        dimensions=dim_scores,
        claims=claims,
        hitl=hitl,
        phi_flagged=phi_flagged,
    )
