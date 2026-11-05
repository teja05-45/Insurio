from app.core.security import hash_password, verify_password


def test_register_login_and_me(client):
    email = "user@example.com"
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "StrongPass123", "full_name": "Asha Rao"},
    )
    assert registered.status_code == 201, registered.text
    body = registered.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == email

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["full_name"] == "Asha Rao"


def test_duplicate_email_is_rejected(client, account):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": account["email"], "password": "StrongPass123"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "email_taken"


def test_weak_password_is_rejected(client):
    response = client.post(
        "/api/v1/auth/register", json={"email": "weak@example.com", "password": "short"}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_wrong_password_returns_generic_error(client, account):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": account["email"], "password": "WrongPass123"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


def test_unauthenticated_request_is_rejected(client):
    response = client.get("/api/v1/documents")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


def test_refresh_tokens_rotate_and_cannot_be_reused(client, account):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": account["email"], "password": account["password"]},
    )
    refresh_token = login.json()["refresh_token"]

    rotated = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert rotated.status_code == 200, rotated.text
    assert rotated.json()["refresh_token"] != refresh_token

    reused = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert reused.status_code == 401


def test_logout_revokes_session(client, account):
    logout = client.post("/api/v1/auth/logout", json={"refresh_token": account["refresh_token"]})
    assert logout.status_code == 200
    after = client.post("/api/v1/auth/refresh", json={"refresh_token": account["refresh_token"]})
    assert after.status_code == 401


def test_password_reset_flow(client, account):
    requested = client.post("/api/v1/auth/forgot-password", json={"email": account["email"]})
    assert requested.status_code == 200
    token = requested.json()["reset_token"]
    assert token

    reset = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "NewStrongPass456"},
    )
    assert reset.status_code == 200

    login = client.post(
        "/api/v1/auth/login",
        json={"email": account["email"], "password": "NewStrongPass456"},
    )
    assert login.status_code == 200


def test_forgot_password_does_not_reveal_unknown_accounts(client):
    response = client.post("/api/v1/auth/forgot-password", json={"email": "nobody@example.com"})
    assert response.status_code == 200
    assert response.json()["reset_token"] is None


def test_password_hashing_round_trip():
    hashed = hash_password("StrongPass123")
    assert hashed != "StrongPass123"
    assert verify_password("StrongPass123", hashed)
    assert not verify_password("WrongPass123", hashed)


def test_profile_update_and_sessions(client, account):
    updated = client.patch(
        "/api/v1/auth/me", json={"full_name": "Asha R."}, headers=account["headers"]
    )
    assert updated.status_code == 200
    assert updated.json()["full_name"] == "Asha R."

    sessions = client.get("/api/v1/auth/sessions", headers=account["headers"])
    assert sessions.status_code == 200
    assert len(sessions.json()) >= 1
