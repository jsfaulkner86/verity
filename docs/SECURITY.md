# Security and Privacy

## Threat model

Verity processes LLM responses that may include:

- Personally identifiable information (PII)
- Protected health information (PHI) when used in clinical contexts
- Confidential business content

It does NOT process credentials or perform authentication; that
boundary belongs to the surrounding system.

## Safe-by-default behaviors

- **No raw prompts in logs.** `verity.observability.logging.hash_prompt`
  produces a 16-char SHA-256 prefix used for correlation. Logs include
  the hash; they never include the full prompt or response.
- **PHI redaction on every string field** passed to `structlog`.
  Implemented as a global processor — callers cannot opt out by
  accident.
- **Audit log redaction.** Claim text is run through `redact_phi`
  before being persisted, even though raw response text is not stored
  there in the first place.
- **PHI-driven escalation.** Any PHI flag in a clinical context routes
  to ESCALATE regardless of composite score.
- **Secret types.** Provider API keys are typed as `pydantic.SecretStr`
  so their values do not appear in `repr()` or default JSON
  serialization.

## What Verity does NOT do

- It is not a HIPAA-grade de-identification system. PHI detection is
  intentionally conservative pattern matching and will miss
  free-text identifiers, indirect identifiers, and quasi-identifiers.
- It does not encrypt logs at rest — that is the operator's concern.
- It does not enforce access control on its own endpoints. Run behind
  an authenticated gateway in any non-development deployment.

## Reporting

Security issues: open a GitHub Security Advisory on the repository,
not a public issue.
