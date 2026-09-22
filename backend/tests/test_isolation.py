"""
Tests for multi-tenant data isolation and security.

Verifies:
1. User A sees only User A's research sessions.
2. User B sees only User B's research sessions.
3. User A cannot access User B's session (IDOR returns 404).
4. User A cannot rename or delete User B's session.
5. Cache keys are strictly isolated per user and session.
6. Unauthenticated requests receive 401.
"""

from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from app.database.connection import Base, engine, init_db
from app.main import app
from app.utils.cache import ResearchCache


@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    yield


@pytest.fixture
def client():
    return TestClient(app)


def _register_and_get_token(client: TestClient, email: str, name: str) -> tuple[dict, str]:
    # Register directly
    resp = client.post(
        "/api/auth/register",
        json={"name": name, "email": email, "password": "SecurePassword123!"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    return data["user"], data["access_token"]


def test_unauthenticated_request_is_rejected(client):
    resp = client.get("/api/research")
    assert resp.status_code == 401


@patch("app.api.routes.research._run_research_pipeline")
def test_multi_user_research_isolation_and_idor_prevention(mock_pipeline, client):
    # 1. Create User A and User B
    user_a, token_a = _register_and_get_token(client, "usera@example.com", "User A")
    user_b, token_b = _register_and_get_token(client, "userb@example.com", "User B")

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 2. User A creates Research Session A
    resp_a = client.post(
        "/api/research",
        json={"goal": "Quantum machine learning algorithms in healthcare"},
        headers=headers_a,
    )
    assert resp_a.status_code == 202
    session_a_id = resp_a.json()["research_id"]

    # 3. User B creates Research Session B
    resp_b = client.post(
        "/api/research",
        json={"goal": "Autonomous agricultural drone architectures"},
        headers=headers_b,
    )
    assert resp_b.status_code == 202
    session_b_id = resp_b.json()["research_id"]

    # 4. User A lists research -> sees ONLY session A
    list_a = client.get("/api/research", headers=headers_a)
    assert list_a.status_code == 200
    ids_a = [s["research_id"] for s in list_a.json()["sessions"]]
    assert session_a_id in ids_a
    assert session_b_id not in ids_a

    # 5. User B lists research -> sees ONLY session B
    list_b = client.get("/api/research", headers=headers_b)
    assert list_b.status_code == 200
    ids_b = [s["research_id"] for s in list_b.json()["sessions"]]
    assert session_b_id in ids_b
    assert session_a_id not in ids_b

    # 6. IDOR Check: User A tries to GET User B's session -> must return 404
    idor_get = client.get(f"/api/research/{session_b_id}", headers=headers_a)
    assert idor_get.status_code == 404

    # 7. IDOR Check: User B tries to GET User A's session -> must return 404
    idor_get_b = client.get(f"/api/research/{session_a_id}", headers=headers_b)
    assert idor_get_b.status_code == 404

    # 8. IDOR Check: User A tries to PATCH (rename) User B's session -> must return 404
    idor_rename = client.patch(
        f"/api/research/{session_b_id}",
        json={"title": "Hacked Title"},
        headers=headers_a,
    )
    assert idor_rename.status_code == 404

    # 9. User A renames own session A -> succeeds
    valid_rename = client.patch(
        f"/api/research/{session_a_id}",
        json={"title": "Quantum ML Study V2"},
        headers=headers_a,
    )
    assert valid_rename.status_code == 200
    assert valid_rename.json()["title"] == "Quantum ML Study V2"

    # 10. IDOR Check: User A tries to DELETE User B's session -> must return 404
    idor_delete = client.delete(f"/api/research/{session_b_id}", headers=headers_a)
    assert idor_delete.status_code == 404

    # 11. User A deletes own session A -> succeeds
    valid_delete = client.delete(f"/api/research/{session_a_id}", headers=headers_a)
    assert valid_delete.status_code == 200

    # Verify session A is deleted for User A
    assert client.get(f"/api/research/{session_a_id}", headers=headers_a).status_code == 404


def test_cache_keys_are_isolated_by_user_and_session():
    task = "Investigate quantum computing state of the art"

    key_user_a = ResearchCache.make_key(task, session_id="session-1", user_id="user-100")
    key_user_b = ResearchCache.make_key(task, session_id="session-1", user_id="user-200")
    key_diff_session = ResearchCache.make_key(task, session_id="session-2", user_id="user-100")

    assert key_user_a != key_user_b
    assert key_user_a != key_diff_session
