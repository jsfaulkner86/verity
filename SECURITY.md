# Security Policy

> **Project:** Verity — LLM Confidence Scoring & Epistemic Verification Layer  
> **Maintainer:** The Faulkner Group  
> **Effective Date:** 2026-05-20  
> **Scope:** All code, configurations, scoring models, RAG pipelines, MCP tool definitions, hallucination detection logic, and healthcare evaluation modules in this repository.

---

## ⚠️ Healthcare & PHI Notice

Verity is designed for deployment in **women's health AI pipelines** where LLM outputs may reference clinical data, patient records, or FHIR resources. Even as a verification/scoring layer, Verity may be exposed to PHI in the claims and sources it evaluates.

- **Do not include real patient data, PHI, or PII in any issue, pull request, commit, or bug report.**
- All example claims, source documents, and evaluation inputs in reports must be **fully synthetic or de-identified**.
- Any vulnerability that allows Verity to leak, persist, or mishandle PHI from evaluated content is automatically **Critical severity** and triggers HIPAA breach assessment.

---

## Supported Versions

| Version | Supported |
|---------|-----------|
| `main` branch (latest) | ✅ Active |
| Tagged releases (`v1.x`) | ✅ Patch support for 12 months post-release |
| All prior versions | ❌ No longer supported |

---

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

### Preferred Channel

Use **GitHub's private Security Advisory** feature:

1. Navigate to the [Security tab](https://github.com/jsfaulkner86/verity/security/advisories/new).
2. Click **"Report a vulnerability"**.
3. Complete the advisory form using the template below.

### Backup Channel

```
security@thefaulknergroupadvisors.com
```

Encrypt sensitive disclosures with the maintainer's GPG key (published at `https://thefaulknergroupadvisors.com/.well-known/security.txt`).

---

## Response SLA

| Severity | Initial Acknowledgment | Triage Complete | Target Patch |
|----------|----------------------|-----------------|--------------|
| Critical (CVSS ≥ 9.0 or PHI exposure) | 24 hours | 48 hours | 7 days |
| High (CVSS 7.0–8.9) | 48 hours | 5 business days | 30 days |
| Medium (CVSS 4.0–6.9) | 5 business days | 10 business days | 60 days |
| Low (CVSS < 4.0) | 10 business days | 20 business days | Next release cycle |

**Any vulnerability with a PHI exposure path is automatically Critical**, regardless of CVSS score.

---

## Vulnerability Report Template

```
### Summary
[One-paragraph description of the vulnerability]

### Affected Component
[ ] Confidence scoring engine     [ ] Source grounding / RAG pipeline
[ ] Hallucination detection logic  [ ] MCP tool definitions
[ ] LLM provider integration       [ ] Healthcare evaluation module
[ ] API / service layer             [ ] Dependency (name + CVE)

### Severity Estimate
CVSS Score (if known): ___
PHI Exposure Risk: [ ] Yes  [ ] No  [ ] Unknown
Score Manipulation Risk: [ ] Yes  [ ] No  [ ] Unknown

### Steps to Reproduce
1.
2.
3.

### Proof of Concept
[Code snippet, API call, or description — use synthetic data only, no real PHI]

### Suggested Fix (optional)

### Environment
- Python version:
- LLM provider(s) tested:
- Deployment context (local / staging / production):
- Dependency snapshot:
```

---

## Scope

### In Scope

- **Score manipulation** — inputs or payloads that force Verity to return artificially high confidence scores for false or hallucinated claims, especially in clinical contexts
- **PHI leakage** — evaluated claims or source documents containing PHI persisting in logs, caches, or external storage
- **Source grounding bypass** — mechanisms that allow ungrounded claims to pass verification checks
- **RAG pipeline injection** — malicious inputs that poison retrieval results or manipulate source attribution
- **LLM provider credential exposure** — API keys for OpenAI, Anthropic, Grok, Perplexity, or other providers leaked in logs or responses
- **MCP tool definition injection** — malformed tool configs that redirect scoring calls to unauthorized endpoints
- **Dependency CVEs** with exploitable attack surfaces in the scoring or RAG pipeline context
- **Healthcare evaluation module flaws** — logic errors that produce systematically incorrect confidence scores for clinical claims

### Out of Scope

- Inherent hallucination behavior in upstream LLMs — report to the respective LLM provider
- Vulnerabilities in LLM provider infrastructure (OpenAI, Anthropic, etc.)
- Social engineering attacks against The Faulkner Group staff
- Theoretical vulnerabilities without a realistic attack path
- Issues in forked or derivative works not maintained by this repository

---

## Security Design Principles

Reports demonstrating a violation of these invariants are treated as high priority:

1. **No PHI persistence** — evaluated content (claims, sources, context) is never persisted to disk, logs, or external storage unless explicitly configured with appropriate data handling controls.
2. **Score integrity** — confidence scores must be derived solely from the provided evidence; no score can be influenced by external state injection.
3. **Provider credential isolation** — LLM API keys are never logged, never included in scoring outputs, and are scoped per-evaluation session.
4. **Audit trail on clinical evaluations** — all scoring events in healthcare contexts are logged with request ID, model version, score, and timestamp.
5. **Deterministic fallback** — when source grounding fails, Verity must return a low-confidence score and explicit uncertainty signal, never a false positive.

---

## Coordinated Disclosure Policy

- The Faulkner Group follows a **90-day coordinated disclosure** window from initial report to public advisory.
- Score manipulation vulnerabilities in clinical contexts may warrant accelerated timelines given patient safety implications.
- Reporters who follow this policy in good faith will be credited (with consent) and are protected from legal action related to good-faith research.

---

## Dependency & Supply Chain Security

- Dependencies are pinned in `pyproject.toml` and/or `requirements.txt`.
- Maintainers run `pip-audit` and `safety check` before every release tag.
- GitHub Dependabot alerts are enabled.
- New dependencies require documented rationale in the PR description.

---

## Secret Scanning & CI Enforcement

- GitHub Secret Scanning is enabled on this repository.
- `.env` files are gitignored; `.env.example` is the only committed config template.
- Any committed secret (even in a branch) must be rotated immediately.
- Pre-commit hooks enforce `detect-secrets` scanning before remote push.

---

## Contact

| Role | Contact |
|------|---------|
| Security Disclosure | security@thefaulknergroupadvisors.com |
| General Maintainer | John Faulkner — github.com/jsfaulkner86 |
| Organization | [The Faulkner Group](https://thefaulknergroupadvisors.com) |

---

*This policy is reviewed quarterly and updated with each major release. Last reviewed: 2026-05-20.*
