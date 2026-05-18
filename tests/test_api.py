"""FastAPI endpoint smoke tests."""

from fastapi.testclient import TestClient

from verity.api.main import app


def test_health():
    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


def test_version():
    with TestClient(app) as client:
        r = client.get("/version")
        assert r.status_code == 200
        body = r.json()
        assert body["env"] == "development"
        assert 0 < body["refine_threshold"] < body["accept_threshold"] <= 1


def test_claims_endpoint():
    with TestClient(app) as client:
        r = client.post(
            "/claims",
            json={"response_text": "Ibuprofen 200 mg reduces inflammation."},
        )
        assert r.status_code == 200
        assert r.json()["claims"]


def test_score_endpoint_writes_audit_log(tmp_path, monkeypatch):
    with TestClient(app) as client:
        r = client.post(
            "/score",
            json={
                "response_text": (
                    "The patient was given 200 mg of ibuprofen. "
                    "This may help with the inflammation."
                ),
                "sources": ["Ibuprofen 200 mg is a standard adult NSAID dose."],
                "source_model": "gpt-4o",
                "domain": "clinical",
            },
        )
    assert r.status_code == 200
    body = r.json()
    assert 0.0 <= body["overall_score"] <= 1.0
    assert body["hitl"]["decision"] in {"ACCEPT", "REFINE", "REJECT", "ESCALATE"}
    assert len(body["dimensions"]) == 4
