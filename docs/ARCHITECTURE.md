# Verity — Architecture

## Position in the stack

```
                  user / app
                      │
                      ▼
              ┌──────────────┐
              │  upstream    │  ChatGPT / Claude / Grok / Perplexity /
              │  LLM         │  internal model
              └──────┬───────┘
                     │  response (+ optional sources)
                     ▼
              ┌──────────────┐
              │   Verity     │  ←─ post-generation middleware
              │              │     scores, classifies, routes
              └──────┬───────┘
                     │  Scorecard + HITL decision
                     ▼
                consumer system
```

Verity is **post-generation**. It does not regenerate, retrieve, or
guard the prompt path. Its sole job is to produce a structured,
auditable verdict on a response that already exists.

## Scoring pipeline

```
ScoreRequest
    │
    ├──► extract_claims (deterministic)         ─► list[Claim]
    │
    ├──► score_source_grounding(response, src) ─► DimensionScore
    ├──► score_factual_consistency(claims, src)─► DimensionScore
    ├──► score_claim_specificity(claims)       ─► DimensionScore
    ├──► score_hedging_calibration(claims)     ─► DimensionScore
    │
    ├──► composite(weights) ──► overall_score
    │
    ├──► detect_phi(response)
    │
    └──► hitl.decide(overall, dims, claims, phi, domain)
         │
         ▼
      HITLRecommendation
         │
         ▼
      ScorecardResult ─► AuditLogger.record (JSONL)
```

The pipeline is pure and deterministic at v0. The four scorers are
designed to be drop-in replaceable: any future LLM-backed scorer can
implement the same `(...) -> DimensionScore` signature and slot in
behind a feature flag without touching `engine.py`.

## Composite weights

Defaults are clinical-leaning:

| Dimension              | Weight |
| ---------------------- | ------ |
| Source grounding       | 0.35   |
| Factual consistency    | 0.35   |
| Claim specificity      | 0.15   |
| Hedging calibration    | 0.15   |

Per-domain weight profiles are planned for v0.2; the weights live in
`verity/scoring/engine.py` as a module-level dict for now.

## HITL routing

Rules, in priority order:

1. **PHI flagged + clinical context** → `ESCALATE` (human review).
2. `overall < refine_threshold` → `REJECT`.
3. `overall < accept_threshold` → `REFINE` (with concrete re-prompt).
4. Otherwise → `ACCEPT`.

The REFINE re-prompt is constructed from:
- the two weakest dimensions, and
- up to three unhedged high-specificity claims (numeric, clinical,
  citation).

## PHI / PII handling

Two layers:

1. **Detection** (`verity.observability.phi.detect_phi`): pattern-based
   match for SSN, phone, email, DOB, MRN, and long numeric IDs. Conservative
   by design — false positives are preferable to misses.
2. **Redaction** (`redact_phi`): every matched substring is replaced with
   a `[REDACTED:<LABEL>]` placeholder.

Both are wired into the logging layer (`_redact_processor` in
`logging.py`) so any string field passed to `structlog` is redacted
before render. The audit logger also defensively redacts claim text
before writing.

**Verity is not a HIPAA-grade de-identification pipeline.** It is the
safe-by-default lower bound on what `verity` itself emits.

## Audit log

`logs/audit.jsonl` is append-only, one `ScorecardResult` per line.
Raw prompt and response text are NEVER written to the audit log — only
the extracted (and redacted) claim text. The retention policy
(`VERITY_AUDIT_RETENTION_DAYS`) is advisory; rotation is delegated to
the operator (logrotate, cron, or a sidecar).

## Threading and async

Scoring is CPU-light and synchronous. The FastAPI endpoints are
declared synchronously so they can be served on either a sync or async
worker. The audit logger uses a process-local lock for write safety
within a single uvicorn worker; multi-worker deployments should use a
shared sink (Kafka, S3, etc.) — not a shared file.

## Extensibility hooks

| Concern                | Where to extend                              |
| ---------------------- | -------------------------------------------- |
| New dimension          | Add scorer to `scoring/dimensions.py`, add to weights, list in engine |
| LLM-backed extractor   | Replace `verity.claims.extractor.extract_claims` |
| New HITL decision      | Add to `core.schemas.HITLDecision`, route in `hitl/router.py` |
| Provider adapter       | Drop a module into `verity/adapters/`        |
| Tracing exporter       | Hook into `observability/logging.py` processors |
