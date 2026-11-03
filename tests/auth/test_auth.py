"""Tests para el módulo de autenticación (registro, login, refresh)."""
import pytest


REGISTER_URL = "/api/auth/register"
LOGIN_URL = "/api/auth/login"
REFRESH_URL = "/api/auth/refresh"

VALID_USER = {
    "email": "test@example.com",
    "password": "secret123",
    "role": "student",
}


# ── Registro ──────────────────────────────────────────────────────────────────

def test_register_returns_tokens(client):
    response = client.post(REGISTER_URL, json=VALID_USER)
    assert response.status_code == 201
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


def test_register_duplicate_email_fails(client):
    client.post(REGISTER_URL, json=VALID_USER)
    response = client.post(REGISTER_URL, json=VALID_USER)
    # El segundo intento debe fallar (email único)
    assert response.status_code in (400, 409, 422, 500)


def test_register_short_password_fails(client):
    response = client.post(REGISTER_URL, json={**VALID_USER, "password": "abc"})
    assert response.status_code == 422


# ── Login ─────────────────────────────────────────────────────────────────────

def test_login_valid_credentials(client):
    client.post(REGISTER_URL, json=VALID_USER)
    response = client.post(LOGIN_URL, json={
        "email": VALID_USER["email"],
        "password": VALID_USER["password"],
    })
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body


def test_login_wrong_password(client):
    client.post(REGISTER_URL, json=VALID_USER)
    response = client.post(LOGIN_URL, json={
        "email": VALID_USER["email"],
        "password": "wrong_password",
    })
    assert response.status_code == 401


def test_login_unknown_email(client):
    response = client.post(LOGIN_URL, json={
        "email": "noexiste@example.com",
        "password": "cualquiera",
    })
    assert response.status_code == 401


# ── Refresh ───────────────────────────────────────────────────────────────────

def test_refresh_returns_new_tokens(client):
    reg = client.post(REGISTER_URL, json=VALID_USER).json()
    response = client.post(REFRESH_URL, json={
        "access_token": reg["access_token"],
        "refresh_token": reg["refresh_token"],
    })
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body


def test_refresh_invalid_token(client):
    response = client.post(REFRESH_URL, json={
        "access_token": "invalid",
        "refresh_token": "invalid",
    })
    assert response.status_code == 401
