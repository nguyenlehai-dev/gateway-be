import os
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.user import User
from app.main import app
from app.services.auth_service import hash_password


client = TestClient(app)


def test_login_and_me_flow() -> None:
    old_auth_enabled = os.environ.get("GATEWAY_AUTH_ENABLED")
    old_auth_secret = os.environ.get("GATEWAY_AUTH_SECRET_KEY")
    db = SessionLocal()
    username = f"test-admin-login-{uuid4().hex[:8]}"
    existing = db.query(User).filter(User.username == username).one_or_none()
    if existing is None:
        db.add(
            User(
                username=username,
                full_name="Gateway Admin",
                password_hash=hash_password("GatewayAdmin@2026!"),
                role="admin",
                status="active",
            )
        )
        db.commit()

    try:
        os.environ["GATEWAY_AUTH_ENABLED"] = "true"
        os.environ["GATEWAY_AUTH_SECRET_KEY"] = "test-auth-secret"
        get_settings.cache_clear()

        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": "GatewayAdmin@2026!"},
        )
        assert login_response.status_code == 200
        login_body = login_response.json()
        assert login_body["user"]["username"] == username
        assert login_body["token_type"] == "bearer"

        me_response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {login_body['access_token']}"},
        )
        assert me_response.status_code == 200
        assert me_response.json()["role"] == "admin"
    finally:
        if old_auth_enabled is None:
            os.environ.pop("GATEWAY_AUTH_ENABLED", None)
        else:
            os.environ["GATEWAY_AUTH_ENABLED"] = old_auth_enabled

        if old_auth_secret is None:
            os.environ.pop("GATEWAY_AUTH_SECRET_KEY", None)
        else:
            os.environ["GATEWAY_AUTH_SECRET_KEY"] = old_auth_secret

        get_settings.cache_clear()
        created = db.query(User).filter(User.username == username).one_or_none()
        if created is not None:
            db.delete(created)
            db.commit()
        db.close()
