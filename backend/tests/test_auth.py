"""Authentication and profile tests."""

from tests.conftest import auth_headers, register_user


def test_register_login_and_me(client):
    payload = register_user(client)
    assert payload["token_type"] == "bearer"
    assert payload["access_token"]
    assert payload["user"]["email"] == "alex@example.com"
    assert "hashed_password" not in payload["user"]

    me = client.get("/api/auth/me", headers=auth_headers(payload["access_token"]))
    assert me.status_code == 200
    assert me.json()["username"] == "Alex"

    login = client.post(
        "/api/auth/login",
        json={"email": "alex@example.com", "password": "StrongPass1"},
    )
    assert login.status_code == 200
    assert login.json()["user"]["id"] == payload["user"]["id"]


def test_duplicate_email_is_rejected(client):
    register_user(client)
    response = client.post(
        "/api/auth/register",
        json={
            "username": "Another Alex",
            "email": "ALEX@example.com",
            "password": "StrongPass1",
        },
    )
    assert response.status_code == 409


def test_weak_password_and_invalid_email_are_rejected(client):
    weak = client.post(
        "/api/auth/register",
        json={"username": "Sam", "email": "sam@example.com", "password": "short"},
    )
    assert weak.status_code == 422

    invalid = client.post(
        "/api/auth/register",
        json={"username": "Sam", "email": "not-an-email", "password": "StrongPass1"},
    )
    assert invalid.status_code == 422


def test_login_failure_and_protected_route(client):
    register_user(client)
    wrong = client.post(
        "/api/auth/login",
        json={"email": "alex@example.com", "password": "WrongPass1"},
    )
    assert wrong.status_code == 401

    unauthorized = client.get("/api/auth/me")
    assert unauthorized.status_code == 401

    invalid_token = client.get(
        "/api/auth/me", headers={"Authorization": "Bearer invalid.token.value"}
    )
    assert invalid_token.status_code == 401


def test_profile_update_and_password_change(client):
    payload = register_user(client)
    headers = auth_headers(payload["access_token"])

    updated = client.put(
        "/api/auth/me",
        json={"username": "Alex Carter", "email": "alex.carter@example.com"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["email"] == "alex.carter@example.com"

    changed = client.put(
        "/api/auth/me/password",
        json={"current_password": "StrongPass1", "new_password": "NewStrong2"},
        headers=headers,
    )
    assert changed.status_code == 200

    old_login = client.post(
        "/api/auth/login",
        json={"email": "alex.carter@example.com", "password": "StrongPass1"},
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/api/auth/login",
        json={"email": "alex.carter@example.com", "password": "NewStrong2"},
    )
    assert new_login.status_code == 200
