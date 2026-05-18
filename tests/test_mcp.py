"""MCP dispatch surface — exercised without spinning up stdio."""

from verity.api.mcp_server import dispatch


def test_tools_list_returns_three_tools():
    result = dispatch("tools/list", {})
    names = {t["name"] for t in result["tools"]}
    assert names == {"score_response", "extract_claims", "get_hitl_decision"}


def test_extract_claims_tool():
    result = dispatch(
        "tools/call",
        {"name": "extract_claims", "arguments": {"response_text": "Ibuprofen reduces pain."}},
    )
    assert "claims" in result


def test_score_response_tool_end_to_end():
    result = dispatch(
        "tools/call",
        {
            "name": "score_response",
            "arguments": {
                "response_text": "Ibuprofen 200 mg reduces inflammation.",
                "sources": ["Ibuprofen 200 mg is a standard adult NSAID dose."],
                "source_model": "gpt-4o",
                "domain": "clinical",
            },
        },
    )
    assert "overall_score" in result
    assert "hitl" in result
