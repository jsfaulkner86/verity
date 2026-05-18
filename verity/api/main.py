"""FastAPI surface for Verity.

Endpoints:
  GET  /health      — liveness probe (used by Docker HEALTHCHECK).
  GET  /version     — package + config snapshot (non-secret).
  POST /score       — score an LLM response. Returns ScorecardResult.
  POST /claims      — extract atomic claims from an LLM response.
  POST /hitl        — compute HITL decision from a pre-built scorecard.

No middleware logs raw request bodies. Correlation IDs are emitted via
structlog contextvars.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Body, Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from verity import __version__
from verity.claims import extract_claims
from verity.config import Settings, get_settings
from verity.core.schemas import (
    Claim,
    HITLRecommendation,
    ScorecardResult,
    ScoreRequest,
)
from verity.hitl.router import decide
from verity.observability.audit import AuditLogger
from verity.observability.audit import get_audit_logger as _get_audit_logger
from verity.observability.logging import configure_logging, get_logger, hash_prompt


@asynccontextmanager
async def _lifespan(app: FastAPI):
    configure_logging()
    log = get_logger("verity.api")
    log.info("verity.startup", version=__version__)
    yield
    log.info("verity.shutdown")


app = FastAPI(
    title="Verity",
    description=(
        "LLM confidence scoring layer — multi-dimensional epistemic "
        "verification for source grounding, factual consistency, claim "
        "specificity, and hedging calibration."
    ),
    version=__version__,
    lifespan=_lifespan,
)


def _audit_dep() -> AuditLogger:
    return _get_audit_logger()


SettingsDep = Annotated[Settings, Depends(get_settings)]
AuditDep = Annotated[AuditLogger, Depends(_audit_dep)]


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = __version__


class VersionResponse(BaseModel):
    version: str
    env: str
    accept_threshold: float
    refine_threshold: float
    healthcare_mode: bool
    phi_detection: bool


class ClaimsRequest(BaseModel):
    response_text: str = Field(..., min_length=1)


class ClaimsResponse(BaseModel):
    claims: list[Claim]


class HITLInput(BaseModel):
    scorecard: ScorecardResult


@app.get("/health", response_model=HealthResponse, tags=["meta"])
def health() -> HealthResponse:
    return HealthResponse()


@app.get("/version", response_model=VersionResponse, tags=["meta"])
def version(settings: SettingsDep) -> VersionResponse:
    return VersionResponse(
        version=__version__,
        env=settings.env,
        accept_threshold=settings.accept_threshold,
        refine_threshold=settings.refine_threshold,
        healthcare_mode=settings.healthcare_mode,
        phi_detection=settings.phi_detection,
    )


@app.post("/score", response_model=ScorecardResult, tags=["scoring"])
def score(
    payload: Annotated[ScoreRequest, Body(...)],
    settings: SettingsDep,
    audit: AuditDep,
) -> ScorecardResult:
    # Import inside the handler to avoid circular import at module load time.
    from verity.scoring.engine import score_response

    log = get_logger("verity.api.score")
    log.info(
        "score.request",
        request_id=payload.request_id,
        source_model=payload.source_model,
        domain=payload.domain,
        prompt_hash=hash_prompt(payload.prompt_text or ""),
        response_hash=hash_prompt(payload.response_text),
        response_chars=len(payload.response_text),
        source_count=len(payload.sources),
    )
    try:
        result = score_response(payload, settings=settings)
    except Exception as exc:  # pragma: no cover — defensive
        log.error("score.error", request_id=payload.request_id, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Scoring failed.",
        ) from exc
    audit.record(result)
    log.info(
        "score.complete",
        request_id=payload.request_id,
        overall_score=result.overall_score,
        decision=result.hitl.decision.value,
        phi_flagged=result.phi_flagged,
    )
    return result


@app.post("/claims", response_model=ClaimsResponse, tags=["scoring"])
def claims(req: ClaimsRequest) -> ClaimsResponse:
    return ClaimsResponse(claims=extract_claims(req.response_text))


@app.post("/hitl", response_model=HITLRecommendation, tags=["scoring"])
def hitl(payload: HITLInput, settings: SettingsDep) -> HITLRecommendation:
    sc = payload.scorecard
    return decide(
        overall_score=sc.overall_score,
        dimensions=list(sc.dimensions),
        claims=list(sc.claims),
        phi_flagged=sc.phi_flagged,
        domain=sc.domain,
        settings=settings,
    )
