"""Verity — LLM confidence scoring layer.

Multi-dimensional epistemic verification for source grounding,
factual consistency, claim specificity, and hedging calibration.
"""

__version__ = "0.1.0"

from verity.core.schemas import (
    Claim,
    ClaimType,
    DimensionScore,
    HITLDecision,
    HITLRecommendation,
    ScorecardResult,
    ScoreRequest,
)

__all__ = [
    "__version__",
    "Claim",
    "ClaimType",
    "DimensionScore",
    "HITLDecision",
    "HITLRecommendation",
    "ScoreRequest",
    "ScorecardResult",
]
