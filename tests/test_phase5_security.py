import os
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app


client = TestClient(app)


def test_auth_enforced_for_admin_write() -> None:
    suffix = uuid4().hex[:8]
    old_enabled = os.environ.get("GATEWAY_AUTH_ENABLED")
    old_tokens = os.environ.get("GATEWAY_AUTH_TOKENS")
    try:
        os.environ["GATEWAY_AUTH_ENABLED"] = "true"
        os.environ["GATEWAY_AUTH_TOKENS"] = "admin:admin-token,operator:operator-token"
        get_settings.cache_clear()

        unauthorized = client.post(
            "/api/v1/vendors",
            json={"name": "Secured", "slug": "secured", "code": "secured", "status": "active"},
        )
        assert unauthorized.status_code == 401

        forbidden = client.post(
            "/api/v1/vendors",
            headers={"Authorization": "Bearer operator-token"},
            json={
                "name": f"Secured {suffix}",
                "slug": f"secured-operator-{suffix}",
                "code": f"secured-operator-{suffix}",
                "status": "active",
            },
        )
        assert forbidden.status_code == 403

        allowed = client.post(
            "/api/v1/vendors",
            headers={"Authorization": "Bearer admin-token"},
            json={
                "name": f"Secured {suffix}",
                "slug": f"secured-admin-{suffix}",
                "code": f"secured-admin-{suffix}",
                "status": "active",
            },
        )
        assert allowed.status_code == 201
    finally:
        if old_enabled is None:
            os.environ.pop("GATEWAY_AUTH_ENABLED", None)
        else:
            os.environ["GATEWAY_AUTH_ENABLED"] = old_enabled

        if old_tokens is None:
            os.environ.pop("GATEWAY_AUTH_TOKENS", None)
        else:
            os.environ["GATEWAY_AUTH_TOKENS"] = old_tokens

        get_settings.cache_clear()
