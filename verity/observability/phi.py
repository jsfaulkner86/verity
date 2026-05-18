"""Lightweight PHI / PII detection and redaction.

Pattern-based, intentionally conservative. The goal is to:
  1. Catch obvious PHI (SSN, MRN, email, phone, DOB) before it lands in logs.
  2. Flag clinical responses that contain anything resembling identifying data.

This is NOT a substitute for a HIPAA-grade de-identification pipeline.
It is the safe-by-default lower bound for what `verity` itself emits.
"""

from __future__ import annotations

import re

_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_PHONE_RE = re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_DOB_RE = re.compile(r"\b(?:0?[1-9]|1[0-2])[/-](?:0?[1-9]|[12]\d|3[01])[/-](?:19|20)\d{2}\b")
_MRN_RE = re.compile(r"\b(?:MRN|mrn|medical record(?:\s+number)?)[:\s#]*([A-Z0-9-]{4,})", re.I)
# Conservative: 6+ digit run that isn't obviously a year.
_LONG_ID_RE = re.compile(r"\b\d{6,}\b")

_PATTERNS = (
    ("SSN", _SSN_RE),
    ("PHONE", _PHONE_RE),
    ("EMAIL", _EMAIL_RE),
    ("DOB", _DOB_RE),
    ("MRN", _MRN_RE),
    ("ID", _LONG_ID_RE),
)


def detect_phi(text: str) -> bool:
    """Return True if any PHI/PII-shaped substring is found."""
    return any(rx.search(text) for _, rx in _PATTERNS)


def redact_phi(text: str) -> str:
    """Return `text` with each PHI pattern replaced by a tagged placeholder."""
    out = text
    for label, rx in _PATTERNS:
        out = rx.sub(f"[REDACTED:{label}]", out)
    return out
