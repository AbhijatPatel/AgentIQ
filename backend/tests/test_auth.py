"""
Tests for authentication and user management.

Uses an in-memory SQLite database so authentication tests
do not require the production PostgreSQL database.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.api.dependencies import get_db
from app.database.connection import Base
from app.main import app


@pytest.fixture
def client():
    """Create a fresh test database and TestClient for each test."""
    engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
    Base.metadata.create_all(engine)

    TestSessionLocal = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
    )

    def override_get_db():
        db = TestSessionLocal()

        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    test_client = TestClient(app)

    yield test_client

    app.dependency_overrides.clear()


def test_register_user_success(client):
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Test User",
            "email": "test@example.com",
            "password": "Test@12345",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["name"] == "Test User"
    assert data["user"]["email"] == "test@example.com"
    assert "password" not in data["user"]
    assert "password_hash" not in data["user"]


def test_register_rejects_duplicate_email(client):
    user_data = {
        "name": "Test User",
        "email": "duplicate@example.com",
        "password": "Test@12345",
    }

    first_response = client.post(
        "/api/auth/register",
        json=user_data,
    )

    assert first_response.status_code == 200

    second_response = client.post(
        "/api/auth/register",
        json=user_data,
    )

    assert second_response.status_code == 409
    detail = second_response.json().get("detail") or second_response.json().get("message")
    assert "already exists" in detail or detail == "Email already registered"


def test_register_rejects_short_password(client):
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Test User",
            "email": "short@example.com",
            "password": "1234567",
        },
    )

    assert response.status_code in (400, 422)


def test_register_rejects_invalid_email(client):
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Test User",
            "email": "invalid-email",
            "password": "Test@12345",
        },
    )

    assert response.status_code == 422


def test_login_success(client):
    register_response = client.post(
        "/api/auth/register",
        json={
            "name": "Login User",
            "email": "login@example.com",
            "password": "Test@12345",
        },
    )

    assert register_response.status_code == 200

    response = client.post(
        "/api/auth/login",
        json={
            "email": "login@example.com",
            "password": "Test@12345",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "login@example.com"


def test_login_rejects_wrong_password(client):
    client.post(
        "/api/auth/register",
        json={
            "name": "Login User",
            "email": "wrong-password@example.com",
            "password": "Test@12345",
        },
    )

    response = client.post(
        "/api/auth/login",
        json={
            "email": "wrong-password@example.com",
            "password": "WrongPassword",
        },
    )

    assert response.status_code == 401

    assert response.json()["message"] == "Invalid email or password"

def test_login_rejects_unknown_email(client):
    response = client.post(
        "/api/auth/login",
        json={
            "email": "unknown@example.com",
            "password": "Test@12345",
        },
    )

    assert response.status_code == 401
    assert (
    response.json().get("detail")
    or response.json().get("message")
) == "Invalid email or password"


def test_get_me_requires_authentication(client):
    response = client.get("/api/auth/me")

    assert response.status_code == 401


def test_get_me_with_valid_token(client):
    register_response = client.post(
        "/api/auth/register",
        json={
            "name": "Me User",
            "email": "me@example.com",
            "password": "Test@12345",
        },
    )

    token = register_response.json()["access_token"]

    response = client.get(
        "/api/auth/me",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["name"] == "Me User"
    assert data["email"] == "me@example.com"
    assert "id" in data
    assert "created_at" in data


def test_get_me_rejects_invalid_token(client):
    response = client.get(
        "/api/auth/me",
        headers={
            "Authorization": "Bearer invalid-token",
        },
    )

    assert response.status_code == 401


@patch("app.api.routes.research.run_agentiq")
def test_research_requires_authentication(mock_run_agentiq, client):
    response = client.post(
        "/api/research",
        json={
            "goal": "Research artificial intelligence",
        },
    )

    assert response.status_code == 401
    mock_run_agentiq.assert_not_called()


@patch("app.api.routes.research.run_agentiq")
def test_authenticated_user_can_start_research(
    mock_run_agentiq,
    client,
):
    mock_run_agentiq.return_value = {
        "tasks": [],
        "evidence": [],
        "revision_count": 0,
        "final_report": None,
        "critique": None,
        "errors": [],
        "agent_events": [],
    }

    register_response = client.post(
        "/api/auth/register",
        json={
            "name": "Research User",
            "email": "research@example.com",
            "password": "Test@12345",
        },
    )

    token = register_response.json()["access_token"]

    response = client.post(
        "/api/research",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "goal": "Research artificial intelligence",
        },
    )

    assert response.status_code == 202

    data = response.json()

    assert "research_id" in data
    assert data["status"] == "running"