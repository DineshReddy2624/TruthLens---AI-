"""Tests for authentication endpoints."""

import pytest


class TestRegister:
    def test_register_success(self, client):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "name": "New User",
                "email": "new@example.com",
                "password": "securepass123",
            },
        )
        assert response.status_code == 201
        assert response.json()["message"] == "User registered successfully"

    def test_register_duplicate_email(self, client, test_user):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "name": "Duplicate",
                "email": "test@example.com",
                "password": "securepass123",
            },
        )
        assert response.status_code == 409

    def test_register_weak_password(self, client):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "name": "Weak",
                "email": "weak@example.com",
                "password": "short",
            },
        )
        assert response.status_code == 422

    def test_register_invalid_email(self, client):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "name": "Bad Email",
                "email": "not-an-email",
                "password": "securepass123",
            },
        )
        assert response.status_code == 422


class TestLogin:
    def test_login_success(self, client, test_user):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "testpassword123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, test_user):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "wrongpassword"},
        )
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "testpassword123"},
        )
        assert response.status_code == 401


class TestRefresh:
    def test_refresh_success(self, client, test_user):
        # First login
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "testpassword123"},
        )
        refresh_token = login_response.json()["refresh_token"]

        # Then refresh
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_refresh_invalid_token(self, client):
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid.token.here"},
        )
        assert response.status_code == 401


class TestMe:
    def test_me_authenticated(self, client, auth_headers):
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["name"] == "Test User"
        assert data["role"] == "user"

    def test_me_no_token(self, client):
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 403

    def test_me_invalid_token(self, client):
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401


class TestHealthCheck:
    def test_health(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
