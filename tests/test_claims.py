"""Claim extractor — classification + hedging + offsets."""

from verity.claims import extract_claims
from verity.core.schemas import ClaimType


def test_extractor_skips_tiny_sentences():
    claims = extract_claims("Hi. Hello.")
    assert claims == []


def test_extractor_finds_numeric_and_clinical():
    text = (
        "The patient was given 200 mg of ibuprofen. "
        "Their blood pressure was 120/80. "
        "I think the prognosis is good."
    )
    claims = extract_claims(text)
    types = {c.type for c in claims}
    assert ClaimType.CLINICAL in types or ClaimType.NUMERIC in types
    # Opinion sentence must be detected.
    assert any(c.type == ClaimType.OPINION for c in claims)


def test_hedging_detection():
    text = "This might cause drowsiness. The dose is 50 mg."
    claims = extract_claims(text)
    hedged = next(c for c in claims if "might" in c.text.lower())
    unhedged = next(c for c in claims if "50 mg" in c.text.lower())
    assert hedged.hedged is True
    assert unhedged.hedged is False


def test_span_offsets_are_valid():
    text = "First sentence here. Second sentence is longer than the first."
    claims = extract_claims(text)
    for c in claims:
        assert c.span is not None
        start, end = c.span
        assert 0 <= start < end <= len(text)
        assert text[start:end].strip() == c.text.strip()


def test_citation_classification():
    text = "See https://example.com/paper for details on the methodology."
    claims = extract_claims(text)
    assert any(c.type == ClaimType.CITATION for c in claims)
