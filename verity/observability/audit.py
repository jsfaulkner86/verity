"""Append-only audit log for scorecards.

Writes one JSON object per line to `settings.audit_log_path`. The full
`ScorecardResult` is persisted; raw prompt/response text is NOT
written here — only the scorecard's claim text (which has already
passed through PHI redaction at log time).

Retention is enforced by an external rotator (cron / logrotate); this
module only writes.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from threading import Lock

from verity.config import Settings, get_settings
from verity.core.schemas import ScorecardResult
from verity.observability.phi import redact_phi


class AuditLogger:
    """Thread-safe append-only JSONL writer for scorecards."""

    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    @property
    def path(self) -> Path:
        return self._path

    def record(self, scorecard: ScorecardResult) -> None:
        payload = scorecard.model_dump(mode="json")
        # Defensive redaction — claim text could carry PHI if the upstream
        # response did, even though detect_phi may have flagged it.
        for claim in payload.get("claims", []):
            if isinstance(claim.get("text"), str):
                claim["text"] = redact_phi(claim["text"])
        line = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        with self._lock:
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")


@lru_cache(maxsize=1)
def get_audit_logger(settings: Settings | None = None) -> AuditLogger:
    cfg = settings or get_settings()
    return AuditLogger(cfg.audit_log_path)
