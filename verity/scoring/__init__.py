"""Scoring engine — combines dimension scorers into a composite scorecard."""

from verity.scoring.dimensions import (
    score_claim_specificity,
    score_factual_consistency,
    score_hedging_calibration,
    score_source_grounding,
)
from verity.scoring.engine import score_response

__all__ = [
    "score_response",
    "score_claim_specificity",
    "score_factual_consistency",
    "score_hedging_calibration",
    "score_source_grounding",
]
