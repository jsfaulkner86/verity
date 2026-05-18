"""Scoring engine — composite scores + dimension behaviors."""

from verity.claims import extract_claims
from verity.core.schemas import HITLDecision, ScoreRequest
from verity.scoring.dimensions import (
    score_claim_specificity,
    score_factual_consistency,
    score_hedging_calibration,
    score_source_grounding,
)
from verity.scoring.engine import score_response


def test_source_grounding_neutral_without_sources():
    sc = score_source_grounding("any response", [])
    assert sc.score == 0.5
    assert sc.evidence_count == 0


def test_source_grounding_rewards_overlap():
    text = "Ibuprofen 200 mg reduces inflammation in adult patients."
    sources = ["Ibuprofen, an NSAID, reduces inflammation. Adult dose: 200 mg."]
    sc = score_source_grounding(text, sources)
    assert sc.score > 0.3


def test_full_pipeline_returns_scorecard():
    req = ScoreRequest(
        response_text=(
            "The patient was given 200 mg of ibuprofen. " "This may help with the inflammation."
        ),
        sources=["Ibuprofen 200 mg is a standard adult NSAID dose for inflammation."],
        source_model="gpt-4o",
        domain="clinical",
    )
    result = score_response(req)
    assert 0.0 <= result.overall_score <= 1.0
    assert len(result.dimensions) == 4
    assert result.hitl.decision in HITLDecision
    assert result.claims  # should have extracted at least one claim


def test_unhedged_clinical_lowers_specificity():
    high_risk = extract_claims(
        "The dose is exactly 500 mg. The diagnosis is confirmed. The biopsy shows malignancy."
    )
    sc = score_claim_specificity(high_risk)
    # Multiple unhedged clinical/numeric claims => density-driven low score.
    assert sc.score < 0.8


def test_hedging_calibration_rewards_hedged_high_risk():
    hedged = extract_claims(
        "The dose might be approximately 500 mg. The diagnosis may be confirmed."
    )
    sc = score_hedging_calibration(hedged)
    # Hedged high-risk + no spurious low-risk hedges => high calibration score.
    assert sc.score > 0.5


def test_factual_consistency_supported_by_sources():
    claims = extract_claims("Ibuprofen is an NSAID. The standard adult dose is 200 mg.")
    sc = score_factual_consistency(
        claims, ["Ibuprofen, an NSAID, has a standard adult dose of 200 mg."]
    )
    assert sc.score > 0.5
