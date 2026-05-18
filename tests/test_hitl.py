"""HITL router — threshold semantics and PHI escalation."""

from verity.config import get_settings
from verity.core.schemas import (
    Claim,
    ClaimType,
    Dimension,
    DimensionScore,
    HITLDecision,
)
from verity.hitl.router import decide


def _dims(score: float) -> list[DimensionScore]:
    return [DimensionScore(dimension=Dimension.SOURCE_GROUNDING, score=score)]


def test_high_score_accepts():
    rec = decide(0.95, _dims(0.95), [], False, "general", get_settings())
    assert rec.decision == HITLDecision.ACCEPT


def test_mid_score_refines_with_prompt():
    claims = [
        Claim(text="The dose is 500 mg.", type=ClaimType.NUMERIC, hedged=False),
    ]
    rec = decide(0.7, _dims(0.7), claims, False, "general", get_settings())
    assert rec.decision == HITLDecision.REFINE
    assert rec.refinement_prompt
    assert "500 mg" in rec.refinement_prompt


def test_low_score_rejects():
    rec = decide(0.3, _dims(0.3), [], False, "general", get_settings())
    assert rec.decision == HITLDecision.REJECT


def test_phi_in_clinical_escalates_over_high_score():
    rec = decide(0.99, _dims(0.99), [], True, "clinical", get_settings())
    assert rec.decision == HITLDecision.ESCALATE
    assert rec.escalation_required is True
