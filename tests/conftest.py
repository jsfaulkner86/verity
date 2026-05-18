"""Shared pytest fixtures.

We force `verity.config.get_settings` to read from a per-test temp
directory so audit logs never escape the test sandbox.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from verity.config import Settings, get_settings
from verity.observability.audit import get_audit_logger


@pytest.fixture(autouse=True)
def _isolated_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    audit_path = tmp_path / "audit.jsonl"
    monkeypatch.setenv("VERITY_ENV", "development")
    monkeypatch.setenv("VERITY_AUDIT_LOG_PATH", str(audit_path))
    monkeypatch.setenv("VERITY_LOG_LEVEL", "WARNING")
    # Bust both lru_caches so the test reads our env.
    get_settings.cache_clear()
    get_audit_logger.cache_clear()
    yield
    get_settings.cache_clear()
    get_audit_logger.cache_clear()


@pytest.fixture
def settings() -> Settings:
    return get_settings()
