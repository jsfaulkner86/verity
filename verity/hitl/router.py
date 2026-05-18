"""HITL routing — translate a composite score into an action.

Decision rules, in priority order:
  1. PHI flagged in a clinical context  -> ESCALATE
  2. overall < refine_threshold          -> REJECT
  3. overall < accept_threshold          -> REFINE
  4. otherwise                           -> ACCEPT
"""

from __future__ import annotations

from collections.abc import Sequence

from verity.config import Settings, get_settings
from verity.core.schemas import (
    Claim,
    ClaimType,
    DimensionScore,
    HITLDecision,
    HITLRecommendation,
)


def _refinement_prompt(
    overall: float, dimensions: Sequence[DimensionScore], claims: Sequence[Claim]
) -> str:
    """Build a concrete re-prompt for the upstream LLM."""
    weak = sorted(dimensions, key=lambda d: d.score)[:2]
    weak_names = ", ".join(d.dimension.value for d in weak)
    unhedged_high_risk = [
        c
        for c in claims
        if c.type in {ClaimType.NUMERIC, ClaimType.CLINICAL, ClaimType.CITATION} and not c.hedged
    ]
    parts = [
        f"Your previous response scored {overall:.2f} on Verity's epistemic check.",
        f"Improve these dimensions: {weak_names}.",
    ]
    if unhedged_high_risk:
        parts.append(
            "Hedge or cite the following high-specificity claim(s): "
            + " | ".join(c.text for c in unhedged_high_risk[:3])
        )
    parts.append(
        "Cite sources where possible, and avoid unsupported numeric or clinical assertions."
    )
    return " ".join(parts)


def decide(
    overall_score: float,
    dimensions: Sequence[DimensionScore],
    claims: Sequence[Claim],
    phi_flagged: bool,
    domain: str,
    settings: Settings | None = None,
) -> HITLRecommendation:
    cfg = settings or get_settings()

    # 1. PHI in clinical context — always escalate to a human reviewer.
    if phi_flagged and (domain == "clinical" or cfg.healthcare_mode):
        return HITLRecommendation(
            decision=HITLDecision.ESCALATE,
            reason="Potential PHI detected in a clinical context; human review required.",
            refinement_prompt=None,
            escalation_required=True,
        )

    if overall_score < cfg.refine_threshold:
        return HITLRecommendation(
            decision=HITLDecision.REJECT,
            reason=(
                f"Composite score {overall_score:.2f} below refine threshold "
                f"{cfg.refine_threshold:.2f}."
            ),
            refinement_prompt=None,
        )

    if overall_score < cfg.accept_threshold:
        return HITLRecommendation(
            decision=HITLDecision.REFINE,
            reason=(
                f"Composite score {overall_score:.2f} between thresholds "
                f"[{cfg.refine_threshold:.2f}, {cfg.accept_threshold:.2f})."
            ),
            refinement_prompt=_refinement_prompt(overall_score, dimensions, claims),
        )

    return HITLRecommendation(
        decision=HITLDecision.ACCEPT,
        reason=f"Composite score {overall_score:.2f} meets accept threshold.",
    )
