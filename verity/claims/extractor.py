"""Heuristic atomic-claim extractor.

This is the v0 extractor: regex + lexicon based. It is deliberately
LLM-free so that scoring is deterministic, cheap, and reproducible for
audit. A future v1 can swap in an LLM-backed extractor behind the same
`extract_claims` contract without touching scoring.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from verity.core.schemas import Claim, ClaimType

# Sentence terminator that respects common abbreviations and decimal numbers.
# Splits on `. ! ?` followed by whitespace + capital/start.
_SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])")

# Hedging cues; presence flips `hedged=True`.
_HEDGE_TERMS = (
    "may",
    "might",
    "could",
    "possibly",
    "perhaps",
    "likely",
    "appears to",
    "seems to",
    "suggests",
    "approximately",
    "roughly",
    "about",
    "around",
    "potentially",
    "presumably",
)

# Strong clinical markers (broad — not a medical thesaurus).
_CLINICAL_TERMS = (
    "patient",
    "diagnosis",
    "diagnose",
    "symptom",
    "treatment",
    "dose",
    "dosage",
    "mg",
    "ml",
    "mcg",
    "drug",
    "medication",
    "contraindication",
    "icd-10",
    "icd10",
    "cpt",
    "lab result",
    "blood pressure",
    "heart rate",
    "ekg",
    "ecg",
    "mri",
    "ct scan",
    "biopsy",
    "prescription",
    "clinical",
    "therapy",
)

_NUMERIC_RE = re.compile(r"\b\d+(?:[.,]\d+)?\s?(?:%|mg|ml|mcg|kg|g|years?|months?|days?)?\b", re.I)
_CITATION_RE = re.compile(
    r"\b(?:https?://\S+|doi:\s?\S+|\[\d+\]|\(\w+(?:\s+et\s+al\.?)?,\s*\d{4}\))",
    re.I,
)
_OPINION_RE = re.compile(
    r"\b(?:i think|i believe|in my opinion|imo|arguably|debatably)\b",
    re.I,
)
_PROCEDURAL_RE = re.compile(
    r"^(?:step\s*\d+|first(?:ly)?|second(?:ly)?|next|then|finally)[,:\s]",
    re.I,
)


def _classify(sentence: str) -> ClaimType:
    s = sentence.lower()
    if _CITATION_RE.search(sentence):
        return ClaimType.CITATION
    if _OPINION_RE.search(s):
        return ClaimType.OPINION
    if _PROCEDURAL_RE.search(sentence):
        return ClaimType.PROCEDURAL
    if any(term in s for term in _CLINICAL_TERMS):
        return ClaimType.CLINICAL
    if _NUMERIC_RE.search(sentence):
        return ClaimType.NUMERIC
    if len(s.split()) >= 4:
        return ClaimType.FACTUAL
    return ClaimType.OTHER


def _is_hedged(sentence: str) -> bool:
    s = sentence.lower()
    return any(term in s for term in _HEDGE_TERMS)


def _split_sentences(text: str) -> Iterable[tuple[int, int, str]]:
    """Yield (start, end, sentence) tuples with offsets into the original text."""
    text = text.strip()
    if not text:
        return
    cursor = 0
    for chunk in _SENT_SPLIT_RE.split(text):
        chunk_stripped = chunk.strip()
        if not chunk_stripped:
            continue
        start = text.find(chunk_stripped, cursor)
        if start < 0:
            start = cursor
        end = start + len(chunk_stripped)
        cursor = end
        yield start, end, chunk_stripped


def extract_claims(response_text: str) -> list[Claim]:
    """Decompose `response_text` into atomic claims.

    Sentences shorter than 3 words are skipped — they rarely encode a
    verifiable assertion. The returned list preserves source order.
    """
    claims: list[Claim] = []
    for start, end, sentence in _split_sentences(response_text):
        if len(sentence.split()) < 3:
            continue
        claims.append(
            Claim(
                text=sentence,
                type=_classify(sentence),
                span=(start, end),
                confidence=0.85,
                hedged=_is_hedged(sentence),
            )
        )
    return claims
