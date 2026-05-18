"""Pydantic v2 schemas for the Verity public surface.

These types are the contract between adapters, scoring, the HITL
router, and the API/MCP layer. Keep them stable; downstream consumers
serialize these to JSON and persist them in audit logs.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class ClaimType(str, Enum):
    """Coarse taxonomy used to weight risk per claim."""

    FACTUAL = "factual"  # verifiable against a source corpus
    NUMERIC = "numeric"  # quantitative, high-precision risk
    CLINICAL = "clinical"  # healthcare / medical assertion
    CITATION = "citation"  # reference, URL, or DOI
    OPINION = "opinion"  # subjective; not directly verifiable
    PROCEDURAL = "procedural"  # how-to / step-based
    OTHER = "other"


class HITLDecision(str, Enum):
    """Routing decision derived from the composite score."""

    ACCEPT = "ACCEPT"  # Pass-through; score >= accept_threshold
    REFINE = "REFINE"  # Send back to LLM with refinement guidance
    REJECT = "REJECT"  # Score < refine_threshold; do not return as-is
    ESCALATE = "ESCALATE"  # Human review required (PHI / high-stakes / low confidence)


class Dimension(str, Enum):
    """Scoring dimensions. Stable string values for downstream analytics."""

    SOURCE_GROUNDING = "source_grounding"
    FACTUAL_CONSISTENCY = "factual_consistency"
    CLAIM_SPECIFICITY = "claim_specificity"
    HEDGING_CALIBRATION = "hedging_calibration"


class _Frozen(BaseModel):
    """Immutable base — scorecards are append-only audit artifacts."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class Claim(_Frozen):
    """A single atomic assertion extracted from an LLM response."""

    text: str = Field(..., min_length=1, description="The atomic claim text.")
    type: ClaimType = Field(default=ClaimType.OTHER)
    span: tuple[int, int] | None = Field(
        default=None,
        description="(start, end) character offsets into the source response, when known.",
    )
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Extractor's confidence that this is a real claim."
    )
    hedged: bool = Field(
        default=False,
        description="Whether the original phrasing was hedged (e.g. 'may', 'might', 'approximately').",
    )


class DimensionScore(_Frozen):
    """Score for one of the four verification dimensions."""

    dimension: Dimension
    score: float = Field(..., ge=0.0, le=1.0)
    rationale: str = Field(
        default="", description="Brief, non-PHI explanation of how the score was derived."
    )
    evidence_count: int = Field(default=0, ge=0)


class ScoreRequest(BaseModel):
    """Input to the scoring pipeline."""

    model_config = ConfigDict(extra="forbid")

    response_text: str = Field(..., min_length=1, description="The raw LLM response to evaluate.")
    prompt_text: str | None = Field(
        default=None, description="Original user prompt. Optional; improves grounding analysis."
    )
    sources: list[str] = Field(
        default_factory=list,
        description="Optional retrieval sources / RAG context the LLM was given.",
    )
    source_model: str | None = Field(
        default=None,
        description="Identifier of the upstream LLM (e.g. 'gpt-4o', 'claude-sonnet-4-6').",
    )
    domain: Literal["general", "clinical", "legal", "financial"] = Field(default="general")
    request_id: str = Field(default_factory=lambda: str(uuid4()))


class HITLRecommendation(_Frozen):
    """Routing recommendation produced by the HITL router."""

    decision: HITLDecision
    reason: str
    refinement_prompt: str | None = Field(
        default=None,
        description="When decision is REFINE, suggested re-prompt to send to the upstream LLM.",
    )
    escalation_required: bool = Field(default=False)


class ScorecardResult(_Frozen):
    """The full scoring artifact — persisted to audit log."""

    request_id: str
    source_model: str | None
    domain: str
    overall_score: float = Field(..., ge=0.0, le=1.0)
    dimensions: list[DimensionScore]
    claims: list[Claim]
    hitl: HITLRecommendation
    phi_flagged: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    verity_version: str = Field(default="0.1.0")
