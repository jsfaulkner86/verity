from verity.adapters.openai import from_openai_response, score_openai_response
from verity.core.schemas import ScoreRequest


def test_from_openai_response_extracts_assistant_text_and_annotations():
    response = {
        "model": "gpt-4.1-mini",
        "output": [
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "output_text",
                        "text": "The 2024 contribution limit was $23,000.",
                        "annotations": [
                            {"type": "url_citation", "url": "https://example.test/irs-2024"}
                        ],
                    },
                    {"type": "refusal", "refusal": "No refusal should be included."},
                    {"type": "tool_call", "name": "lookup"},
                ],
            }
        ],
    }

    request = from_openai_response(response)

    assert isinstance(request, ScoreRequest)
    assert request.response_text == "The 2024 contribution limit was $23,000."
    assert request.sources == ["https://example.test/irs-2024"]
    assert request.source_model == "gpt-4.1-mini"
    assert request.domain == "general"


def test_from_openai_response_respects_explicit_sources_and_scores():
    response = {
        "model": "gpt-4.1-mini",
        "output_text": "Paris is the capital of France.",
    }

    request = from_openai_response(response, sources=["France's capital is Paris."])
    result = score_openai_response(response, sources=["France's capital is Paris."])

    assert request.sources == ["France's capital is Paris."]
    assert result.request_id
    assert result.source_model == "gpt-4.1-mini"
    assert 0 <= result.overall_score <= 1
