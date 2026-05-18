"""Schema invariants — frozen scorecards, threshold validation."""

import pytest
from pydantic import ValidationError

from verity.core.schemas import (
    Claim,
    ClaimType,
    Dimension,
    DimensionScore,
    HITLDecision,
    HITLRecommendation,
    ScorecardResult,
)


def test_claim_rejects_empty_text():
    with pytest.raises(ValidationError):
        Claim(text="")


def test_dimension_score_bounds():
    with pytest.raises(ValidationError):
        DimensionScore(dimension=Dimension.SOURCE_GROUNDING, score=1.5)


def test_scorecard_is_frozen():
    sc = ScorecardResult(
        request_id="r-1",
        source_model="gpt-4o",
        domain="general",
        overall_score=0.9,
        dimensions=[],
        claims=[],
        hitl=HITLRecommendation(decision=HITLDecision.ACCEPT, reason="ok"),
    )
    with pytest.raises(ValidationError):
        sc.overall_score = 0.1  # type: ignore[misc]
    assert sc.verity_version  # populated from default


def test_claim_type_enum_stable_values():
    assert ClaimType.CLINICAL.value == "clinical"
    assert HITLDecision.ESCALATE.value == "ESCALATE"
