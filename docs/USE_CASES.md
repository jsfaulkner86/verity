# Use cases

Each walkthrough below is end-to-end: a representative response, what Verity returns, and how the calling system acts on the verdict. Verity does not call the upstream LLM in these examples — it scores the response *after* generation.

For all examples below, `score_response` is imported as:

```python
from verity.core.schemas import ScoreRequest
from verity.scoring import score_response
```

---

## 1. RAG answer review (ChatGPT / Claude / open-source RAG stacks)

**Workflow.** You retrieve `k` chunks, ask the model to answer using only those chunks, and need to know whether it actually did.

```python
result = score_response(ScoreRequest(
    response_text=(
        "The 2024 policy raised the contribution limit to $23,000 for "
        "participants under 50, with a $7,500 catch-up for those 50 and over."
    ),
    sources=[
        "For 2024, the elective deferral limit is $23,000.",
        "The age 50+ catch-up contribution remains $7,500 for 2024.",
    ],
    source_model="gpt-4o",
    domain="general",
))

if result.hitl.decision.value == "ACCEPT":
    return result  # ship the answer
elif result.hitl.decision.value == "REFINE":
    return retry_with(result.hitl.refinement_prompt)
else:
    return fallback()
```

**What Verity catches.** Answers that *paraphrase* the retrieved chunks without resting on them — common when the model leans on prior weights instead of the supplied context. Source grounding drops, factual consistency may stay high, and the composite lands in REFINE with a re-prompt that cites the weakest dimension.

---

## 2. Web-search summarization (Perplexity, Grok)

**Workflow.** A search-grounded model returns an answer with citations. You want to flag answers whose claims drift from the cited URLs.

```python
result = score_response(ScoreRequest(
    response_text=(
        "Apple shipped the M4 chip in May 2024 across the iPad Pro line, "
        "with a 38% CPU improvement over the M2."
    ),
    sources=[
        "Apple announced the M4 chip on May 7, 2024, debuting in the new iPad Pro.",
        # Note: no source mentions a 38% CPU improvement number.
    ],
    source_model="sonar-pro",
    domain="general",
))
```

**What Verity catches.** The unhedged numeric claim (`38%`) has no supporting source span. Factual consistency drops; claim specificity is high but hedging calibration is low (a high-precision number with no hedge and no support). The HITL refinement prompt explicitly calls out the unsupported numeric claim.

---

## 3. Clinical Q&A / decision support

**Workflow.** A clinician-facing assistant answers using internal guidelines. Any PHI in the response, or any low-confidence clinical claim, must route to a human.

```python
result = score_response(ScoreRequest(
    response_text=(
        "For an adult patient, start with 400 mg ibuprofen every 6 hours "
        "as needed for pain; do not exceed 3,200 mg per day."
    ),
    sources=[
        "Adult ibuprofen dosing: 200–400 mg PO every 4–6 hours PRN, "
        "max 3,200 mg/day per FDA labeling.",
    ],
    source_model="claude-sonnet-4-6",
    domain="clinical",
))
```

**What Verity does differently in `clinical`.** Thresholds are tighter by default, the HITL router escalates on any PHI flag regardless of composite score, and unhedged numeric / clinical claims drive the refinement prompt rather than generic guidance. The audit log row carries the redacted claim text so a reviewer can reconstruct *what* was claimed without re-exposing PHI.

---

## 4. Internal copilots over private docs

**Workflow.** A copilot answers questions against your internal docs. You need an audit trail of every accepted answer and a way to detect drift when you swap models or update prompts.

```python
result = score_response(ScoreRequest(
    response_text=answer,
    sources=retrieved_chunks,
    source_model=current_model_id,
    domain="general",
))

audit_logger.record(result)  # one JSON line per scorecard
```

**What you get.** Every accepted answer is one append-only line in `VERITY_AUDIT_LOG_PATH` with the scorecard, per-dimension rationale, and (redacted) claim list. Diffing those scorecards across model versions or prompt changes turns "did the upgrade hurt us?" from a vibe into a number.

---

## 5. Agent self-check before tool use

**Workflow.** An agent is about to take an irreversible action (email send, ticket creation, SQL write). It runs Verity on its own intended-action summary first, and branches on the verdict.

```python
intent = "I will send a refund of $237.40 to customer #88421."

result = score_response(ScoreRequest(
    response_text=intent,
    sources=[order_context, refund_policy_excerpt],
    source_model="gpt-4o",
    domain="financial",
))

if result.hitl.decision.value == "ACCEPT":
    tools.refund(customer_id=88421, amount=237.40)
else:
    tools.escalate_to_human(scorecard=result)
```

**What Verity adds.** A cheap, deterministic verdict the agent can branch on without another LLM call. Unhedged high-precision financial claims that aren't grounded in policy context route to ESCALATE — exactly the behavior you want before money moves.

---

## 6. Eval pipelines and offline grading

**Workflow.** You're comparing model versions or prompt variants over a fixed eval set and want a reproducible per-dimension score rather than a single opaque rubric.

```python
for example in eval_set:
    for model_id, response in candidate_responses(example).items():
        result = score_response(ScoreRequest(
            response_text=response,
            sources=example.sources,
            source_model=model_id,
            domain=example.domain,
        ))
        writer.write({
            "example_id": example.id,
            "model": model_id,
            "overall": result.overall_score,
            "dims": {d.dimension.value: d.score for d in result.dimensions},
            "decision": result.hitl.decision.value,
        })
```

**What you get.** A reproducible matrix of per-dimension scores you can diff across runs. Because v0.1 scoring is deterministic, identical inputs produce identical scorecards — regressions show up as score deltas, not as flaky test runs.

---

## Tips that apply to every workflow

- **Always pass `sources` when you have them.** Source grounding and factual consistency degrade gracefully when sources are missing, but they're the dimensions with the most signal when sources are present.
- **Set `source_model`.** It's persisted in the audit log and makes cross-model regressions trivial to spot.
- **Use `domain` deliberately.** `clinical`, `legal`, and `financial` tighten behavior compared to `general`; don't reach for them unless you want that tightening.
- **Treat REFINE as a real branch.** The router constructs a concrete re-prompt targeting the weakest two dimensions; sending it back to the upstream model is usually cheaper than escalating to a human.
