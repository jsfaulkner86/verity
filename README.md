# Verity

> **LLM confidence scoring layer — multi-dimensional epistemic verification for source grounding, factual consistency, claim specificity, and hedging calibration.**

Verity is post-generation middleware. It sits *between* any upstream LLM
(ChatGPT, Claude, Grok, Perplexity, an internal model) and the system
that consumes its output, and answers four questions in a single pass:

| Dimension              | Question                                                                 |
| ---------------------- | ------------------------------------------------------------------------ |
| Source grounding       | Does the response actually rest on the retrieval context it was given?   |
| Factual consistency    | Are the verifiable claims supported by the supplied sources?             |
| Claim specificity      | How dense are high-precision (numeric, clinical, citation) claims?       |
| Hedging calibration    | Is uncertainty language matched to the risk of each claim?               |

Each dimension produces a `[0.0, 1.0]` score with a short rationale.
A weighted composite drives a routing decision — **ACCEPT**, **REFINE**,
**REJECT**, or **ESCALATE** — so downstream systems can act on the
verdict instead of guessing.

The package ships PHI-safe defaults: structured logs redact obvious
PHI/PII patterns by default, raw prompt/response text is hashed for
correlation rather than logged verbatim, and any PHI flagged in a
clinical context escalates regardless of score.

---

## Quickstart

```bash
# 1. Install (Python 3.11+)
pip install -e ".[dev]"

# 2. Configure
cp .env.example .env
# edit .env — set provider keys you need, adjust thresholds

# 3. Run the API
make run                       # uvicorn on http://localhost:8080
curl localhost:8080/health
```

### Score a response

```bash
curl -s localhost:8080/score \
  -H 'content-type: application/json' \
  -d '{
        "response_text": "The patient was given 200 mg of ibuprofen.",
        "sources": ["Ibuprofen 200 mg is a standard adult NSAID dose."],
        "source_model": "gpt-4o",
        "domain": "clinical"
      }' | jq
```

The response is a `ScorecardResult` with per-dimension scores, atomic
claims, and an HITL recommendation including a concrete refinement
prompt when the score lands in the REFINE band.

### Use the library directly

```python
from verity.core.schemas import ScoreRequest
from verity.scoring import score_response

result = score_response(ScoreRequest(
    response_text="Ibuprofen 200 mg reduces inflammation.",
    sources=["Ibuprofen 200 mg is a standard adult NSAID dose."],
    domain="clinical",
))

print(result.overall_score, result.hitl.decision)
```

### MCP

`.mcp.json` declares three tools — `score_response`, `extract_claims`,
`get_hitl_decision` — served by `python -m verity.api.mcp_server` over
stdio. The dispatcher in `verity.api.mcp_server.dispatch()` is exported
for direct integration with any MCP SDK.

---

## Configuration

All runtime knobs are environment variables (see `.env.example`).
Important ones:

| Var                            | Default | Purpose                                                |
| ------------------------------ | ------- | ------------------------------------------------------ |
| `VERITY_ACCEPT_THRESHOLD`      | `0.80`  | `overall >= this` → ACCEPT                             |
| `VERITY_REFINE_THRESHOLD`      | `0.55`  | `overall < this` → REJECT; between → REFINE            |
| `VERITY_HEALTHCARE_MODE`       | `true`  | Treat PHI flag as automatic ESCALATE                   |
| `VERITY_PHI_DETECTION`         | `true`  | Run PHI/PII pattern detection on responses             |
| `VERITY_AUDIT_LOG_PATH`        | `./logs/audit.jsonl` | Append-only JSONL audit sink             |
| `VERITY_AUDIT_RETENTION_DAYS`  | `90`    | Advisory retention (rotation handled externally)       |

Thresholds are validated: `refine_threshold` must be strictly less
than `accept_threshold`.

---

## Observability

* **Structured logs** via `structlog`. Console renderer in dev,
  JSON renderer otherwise. A global processor redacts PHI/PII from
  every string field before render — callers cannot accidentally log
  raw prompts.
* **Prompt/response hashing**: `verity.observability.logging.hash_prompt`
  produces a stable 16-char SHA-256 prefix used for correlation in logs.
* **Append-only audit log**: every `ScorecardResult` is written as one
  JSON line to `VERITY_AUDIT_LOG_PATH`. The full scorecard is
  preserved; claim text is redacted defensively before write.
* **Optional tracing**: set `LANGSMITH_API_KEY` for LangSmith, or
  `OTEL_EXPORTER_OTLP_ENDPOINT` for an OpenTelemetry collector. Wiring
  is left to the caller — the package does not auto-export traces by
  default to avoid silent egress of sensitive content.

---

## Repository layout

```
verity/
├── __init__.py
├── config.py              # pydantic-settings; thresholds, keys, paths
├── core/
│   └── schemas.py         # Claim, DimensionScore, ScorecardResult, HITL*
├── claims/
│   └── extractor.py       # deterministic, LLM-free atomic-claim extractor
├── scoring/
│   ├── dimensions.py      # four dimension scorers
│   └── engine.py          # composite + audit-write + HITL routing
├── hitl/
│   └── router.py          # ACCEPT / REFINE / REJECT / ESCALATE rules
├── observability/
│   ├── logging.py         # structlog config with PHI redaction
│   ├── phi.py             # detection + redaction primitives
│   └── audit.py           # append-only JSONL audit logger
├── api/
│   ├── main.py            # FastAPI: /health /version /score /claims /hitl
│   └── mcp_server.py      # MCP stdio server + dispatch()
└── adapters/              # provider adapter stubs (OpenAI, Anthropic, …)
tests/                     # pytest suite
docs/                      # ARCHITECTURE.md, SECURITY.md
```

---

## Development

```bash
make dev            # install with dev + langsmith extras
make test           # pytest
make test-cov       # pytest + coverage
make lint           # ruff
make format         # black
make typecheck      # mypy --strict
make docker-build   # build container image
make docker-run     # docker compose up
```

Tests are deterministic and self-contained — they use a tmp-path audit
log via `tests/conftest.py` and never touch the network.

---

## Roadmap (post-0.1)

* LLM-backed claim extractor behind the same `extract_claims` contract.
* Per-domain weight profiles (clinical vs legal vs general).
* HITL escalation queue integration (webhook + dead-letter).
* OpenTelemetry span auto-export with content-aware sampling.
* Adapters: stream wrappers for OpenAI, Anthropic, Perplexity, xAI.

## License

MIT.
