"""OpenAI Responses API adapter.

Converts an already-returned OpenAI Responses object, or its ``model_dump()``
dict, into Verity's ``ScoreRequest``. This module does not call OpenAI.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

from verity.core.schemas import ScoreRequest
from verity.scoring import score_response

Domain = Literal["general", "clinical", "legal", "financial"]


def _as_mapping(response: Any) -> Mapping[str, Any]:
    if isinstance(response, Mapping):
        return response
    if hasattr(response, "model_dump"):
        dumped = response.model_dump()
        if isinstance(dumped, Mapping):
            return dumped
    raise TypeError("response must be a mapping or expose model_dump()")


def _iter_items(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _block_type(block: Mapping[str, Any]) -> str:
    return str(block.get("type") or block.get("role") or "")


def _text_from_block(block: Mapping[str, Any]) -> str:
    block_type = _block_type(block)
    if block_type in {"refusal", "tool_call", "function_call", "reasoning"}:
        return ""

    if isinstance(block.get("text"), str):
        return block["text"]
    if isinstance(block.get("content"), str):
        return block["content"]

    return ""


def _collect_text_blocks(response: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    blocks: list[Mapping[str, Any]] = []

    for item in _iter_items(response.get("output")):
        if not isinstance(item, Mapping):
            continue
        if item.get("role") not in {None, "assistant"}:
            continue
        for content in _iter_items(item.get("content")):
            if isinstance(content, Mapping):
                blocks.append(content)

    for content in _iter_items(response.get("content")):
        if isinstance(content, Mapping):
            blocks.append(content)

    if isinstance(response.get("output_text"), str):
        blocks.append({"type": "output_text", "text": response["output_text"]})

    return blocks


def _annotation_sources(blocks: list[Mapping[str, Any]]) -> list[str]:
    sources: list[str] = []
    seen: set[str] = set()

    for block in blocks:
        for ann in _iter_items(block.get("annotations")):
            if not isinstance(ann, Mapping):
                continue
            value = ann.get("url") or ann.get("filename") or ann.get("file_id") or ann.get("title")
            if not value:
                continue
            source = str(value)
            if source not in seen:
                sources.append(source)
                seen.add(source)

    return sources


def from_openai_response(
    response: Any,
    *,
    sources: list[str] | None = None,
    domain: Domain = "general",
) -> ScoreRequest:
    """Build a ``ScoreRequest`` from an OpenAI Responses API result."""

    data = _as_mapping(response)
    blocks = _collect_text_blocks(data)
    response_text = "\n".join(text for block in blocks if (text := _text_from_block(block))).strip()
    if not response_text:
        raise ValueError("response does not contain assistant text")

    return ScoreRequest(
        response_text=response_text,
        sources=sources if sources is not None else _annotation_sources(blocks),
        source_model=str(data["model"]) if data.get("model") else None,
        domain=domain,
    )


def score_openai_response(
    response: Any,
    *,
    sources: list[str] | None = None,
    domain: Domain = "general",
):
    """Convert an OpenAI response and score it in one synchronous call."""

    return score_response(from_openai_response(response, sources=sources, domain=domain))
