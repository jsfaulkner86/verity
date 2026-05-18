# Contributing to Verity

Thanks for considering a contribution. Verity is a small, deliberately narrow library: a post-generation confidence-scoring layer for LLM responses, with HITL routing and an audit trail. Contributions that sharpen that narrow focus are very welcome; contributions that expand it should start with a short discussion in an issue first.

## TL;DR

1. Fork, branch from `main`, keep the change focused.
2. `make dev && make test && make lint && make typecheck` should pass.
3. New behavior gets a deterministic test (no network, no flakiness).
4. PHI / raw prompts / raw responses must never appear in logs, audit records, or test fixtures.
5. Open a PR with a one-paragraph "why" and a "how to verify" section.

## Dev loop

```bash
make dev            # editable install + dev + langsmith extras
make test           # pytest, full suite
make test-cov       # with coverage
make lint           # ruff
make format         # black
make typecheck      # mypy --strict
```

The audit logger writes to a tmp path during tests (`tests/conftest.py`). Tests are sync, deterministic, and offline — please keep them that way.

## Scope guardrails

Before writing code, sanity-check the change against these:

- **Post-generation only.** Verity scores responses; it doesn't retrieve, regenerate, or guard prompts. If your change touches the prompt path, it probably belongs in a different layer.
- **Provider-agnostic core.** The scoring pipeline takes plain text + optional sources. Provider specifics live in `verity/adapters/`.
- **Deterministic by default.** Anything stochastic goes behind a flag and ships with a deterministic fallback.
- **Stable public schemas.** `verity.core.schemas` is the contract downstream consumers persist. Additive changes only; never break existing field semantics.
- **PHI-safe defaults.** New code paths must route any string-bearing log/audit through the existing redaction layer.

## Where to start

Issues tagged `good first issue` are scoped to one file and one concept. If none are open, these are reliably useful entry points:

### Provider adapters — `verity/adapters/`

Each adapter is a thin stream wrapper that turns a provider response (and any retrieval context it carried) into a `ScoreRequest`. Targets we'd love:

- OpenAI (`Responses` API + classic Chat Completions)
- Anthropic (Messages API + tool use)
- Perplexity (Sonar online responses with citations)
- xAI / Grok
- Mistral, Bedrock, Vertex, Together, Groq

A good adapter PR includes: the adapter module, one example call in `docs/USE_CASES.md`, and a unit test that feeds a fixture response through the adapter into `score_response`.

### New scoring dimensions — `verity/scoring/dimensions.py`

A dimension scorer is `(...) -> DimensionScore`. Slot it into the engine's weights dict and add a row to the README table. Ideas:

- Citation resolvability (do cited URLs / DOIs actually exist?)
- Temporal coherence (do date / version claims agree with each other?)
- Prompt-injection signal (was the response steered by injected instructions?)
- Self-consistency over `n` samples (when the caller can afford it)

### Domain weight profiles — `verity/scoring/engine.py`

Defaults are clinical-leaning. We want tuned profiles for `legal`, `financial`, and a tighter `general`. Bring evidence (a small held-out set, eval numbers) when proposing a profile.

### HITL queue backends — `verity/hitl/`

The router emits an `HITLRecommendation`. Today there's no shipping queue integration. Useful targets: webhook POST, Slack / Teams notifier, S3 / Kafka dead-letter for `ESCALATE`.

### Examples and walkthroughs — `docs/USE_CASES.md`

End-to-end stories beat API reference. Good candidates: a RAG pipeline that uses Verity for accept/refine; an agent that self-checks before tool use; an eval pipeline that diffs scorecards across model versions.

### Eval harness — new under `tests/eval/`

A reproducible harness that runs Verity over a public RAG benchmark and emits scorecard summaries. Goal: catch regressions in scoring quality, not just code.

## Pull-request checklist

- [ ] Branch is rebased on `main` and the diff is focused on a single concern.
- [ ] `make test lint typecheck` all pass locally.
- [ ] New behavior is covered by a deterministic test.
- [ ] No raw prompts, raw responses, or PHI in code, fixtures, or logs.
- [ ] Public schemas are unchanged, or the change is strictly additive with a migration note.
- [ ] README / `docs/` updated when behavior or configuration changed.
- [ ] PR description explains *why*, not just *what*, and lists how to verify.

## Reporting issues

- **Bugs**: please include a minimal `ScoreRequest` payload and the observed vs. expected `ScorecardResult`.
- **Feature requests**: explain the workflow first; the API second.
- **Security issues**: open a GitHub Security Advisory, not a public issue. See `docs/SECURITY.md`.

## Code of conduct

Be direct, be kind, assume good faith. Reviews focus on the change, not the contributor. We default to merging small, well-scoped PRs quickly and discussing larger ones in an issue before code lands.

## License

By contributing, you agree your contribution is licensed under the MIT License (see `LICENSE`).
