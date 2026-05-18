"""MCP (Model Context Protocol) server stub for Verity.

The `.mcp.json` at the repo root declares three tools (`score_response`,
`extract_claims`, `get_hitl_decision`) and points the MCP runtime at
`python -m verity.api.mcp_server`.

This module exposes a minimal stdio JSON-RPC loop that wires those
tools to the same scoring/claims/hitl primitives used by the HTTP
service. It is intentionally dependency-free so the package can ship
without pulling a heavy MCP SDK; callers that want a full SDK
integration can adapt `dispatch()` directly.
"""

from __future__ import annotations

import json
import sys
from typing import Any

from verity import __version__
from verity.claims import extract_claims
from verity.config import get_settings
from verity.core.schemas import ScorecardResult, ScoreRequest
from verity.hitl.router import decide
from verity.observability.logging import configure_logging, get_logger


def _tool_score_response(args: dict[str, Any]) -> dict[str, Any]:
    from verity.scoring.engine import score_response

    request = ScoreRequest(**args)
    result = score_response(request, settings=get_settings())
    return result.model_dump(mode="json")


def _tool_extract_claims(args: dict[str, Any]) -> dict[str, Any]:
    text = args.get("response_text")
    if not isinstance(text, str) or not text:
        raise ValueError("response_text is required and must be a non-empty string.")
    return {"claims": [c.model_dump(mode="json") for c in extract_claims(text)]}


def _tool_get_hitl_decision(args: dict[str, Any]) -> dict[str, Any]:
    sc = ScorecardResult(**args["scorecard"])
    rec = decide(
        overall_score=sc.overall_score,
        dimensions=list(sc.dimensions),
        claims=list(sc.claims),
        phi_flagged=sc.phi_flagged,
        domain=sc.domain,
        settings=get_settings(),
    )
    return rec.model_dump(mode="json")


TOOLS = {
    "score_response": _tool_score_response,
    "extract_claims": _tool_extract_claims,
    "get_hitl_decision": _tool_get_hitl_decision,
}


def dispatch(method: str, params: dict[str, Any]) -> dict[str, Any]:
    """Pure-function dispatch — exported for tests and SDK integrations."""
    if method == "tools/list":
        return {"tools": [{"name": name, "input_schema": {"type": "object"}} for name in TOOLS]}
    if method == "tools/call":
        name = params.get("name")
        if name not in TOOLS:
            raise ValueError(f"Unknown tool: {name}")
        return TOOLS[name](params.get("arguments") or {})
    raise ValueError(f"Unknown method: {method}")


def _serve_stdio() -> None:  # pragma: no cover — requires interactive stdin.
    """Minimal newline-delimited JSON-RPC loop on stdin/stdout."""
    configure_logging()
    log = get_logger("verity.mcp")
    log.info("verity.mcp.startup", version=__version__)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            result = dispatch(req["method"], req.get("params") or {})
            resp = {"jsonrpc": "2.0", "id": req.get("id"), "result": result}
        except Exception as exc:
            resp = {
                "jsonrpc": "2.0",
                "id": req.get("id") if isinstance(req, dict) else None,
                "error": {"code": -32000, "message": str(exc)},
            }
        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":  # pragma: no cover
    _serve_stdio()
