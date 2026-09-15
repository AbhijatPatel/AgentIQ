"""
Tests for global error handling.

Verifies that different exception types get classified into the
correct HTTP status codes and consistent JSON error shapes.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.utils.error_handlers import register_error_handlers


def _build_test_app():
    """Build a minimal FastAPI app with routes that raise specific errors,
    purely for testing the error handler in isolation."""
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/raise-llm-error")
    def raise_llm_error():
        from app.llm.client import LLMClientError
        raise LLMClientError("Groq timed out")

    @app.get("/raise-generic-error")
    def raise_generic_error():
        raise ValueError("something unexpected broke")

    @app.get("/raise-http-404")
    def raise_http_404():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Not found")

    @app.post("/validate-me")
    def validate_me(payload: dict):
        return payload

    return app


client = TestClient(_build_test_app(), raise_server_exceptions=False)


def test_llm_client_error_returns_502_with_consistent_shape():
    response = client.get("/raise-llm-error")

    assert response.status_code == 502
    data = response.json()
    assert data["error"] == "llm_error"
    assert "message" in data


def test_unclassified_error_returns_500():
    response = client.get("/raise-generic-error")

    assert response.status_code == 500
    data = response.json()
    assert data["error"] == "internal_error"
    assert "message" in data


def test_http_exception_preserves_status_code():
    response = client.get("/raise-http-404")

    assert response.status_code == 404
    data = response.json()
    assert data["error"] == "http_error"
    assert data["message"] == "Not found"