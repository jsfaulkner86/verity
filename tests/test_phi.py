"""PHI detection and redaction."""

from verity.observability.phi import detect_phi, redact_phi


def test_detects_ssn_email_phone_dob():
    text = "Pt John Doe, SSN 123-45-6789, DOB 04/12/1985, email j@x.com, phone (415) 555-1234."
    assert detect_phi(text) is True


def test_redacts_each_pattern():
    text = "SSN 123-45-6789 email a@b.com phone 415-555-1234 DOB 1/2/1990 MRN: ABC1234"
    out = redact_phi(text)
    assert "123-45-6789" not in out
    assert "a@b.com" not in out
    assert "415-555-1234" not in out
    assert "1/2/1990" not in out
    assert "ABC1234" not in out
    assert "[REDACTED:" in out


def test_clean_text_passes_through():
    text = "Ibuprofen reduces inflammation."
    assert detect_phi(text) is False
    assert redact_phi(text) == text
