from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_vendor_crud_flow() -> None:
    suffix = uuid4().hex[:8]
    create_response = client.post(
        "/api/v1/vendors",
        json={
            "name": f"Google {suffix}",
            "slug": f"google-{suffix}",
            "code": f"google-{suffix}",
            "description": "Vendor",
            "status": "active",
        },
    )
    assert create_response.status_code == 201
    vendor = create_response.json()
    vendor_id = vendor["id"]

    list_response = client.get("/api/v1/vendors")
    assert list_response.status_code == 200
    assert list_response.json()["total"] >= 1

    update_response = client.patch(f"/api/v1/vendors/{vendor_id}", json={"description": "Updated vendor"})
    assert update_response.status_code == 200
    assert update_response.json()["description"] == "Updated vendor"


def test_pool_and_api_function_crud_flow() -> None:
    suffix = uuid4().hex[:8]
    vendor_response = client.post(
        "/api/v1/vendors",
        json={
            "name": f"Google Two {suffix}",
            "slug": f"google-two-{suffix}",
            "code": f"google-two-{suffix}",
            "description": "Vendor two",
            "status": "active",
        },
    )
    vendor_id = vendor_response.json()["id"]

    pool_response = client.post(
        "/api/v1/pools",
        json={
            "vendor_id": vendor_id,
            "name": f"Gemini API {suffix}",
            "slug": f"gemini-api-{suffix}",
            "code": f"gemini-api-{suffix}",
            "description": "Pool",
            "status": "active",
            "config_json": {"timeout_seconds": 60},
        },
    )
    assert pool_response.status_code == 201
    pool_id = pool_response.json()["id"]

    api_function_response = client.post(
        "/api/v1/api-functions",
        json={
            "pool_id": pool_id,
            "name": f"Text Generation {suffix}",
            "code": f"text-generation-{suffix}",
            "description": "Function",
            "http_method": "post",
            "path": f"/api/v1/gateway/functions/text-generation-{suffix}/execute",
            "provider_action": "google.genai.text_generation",
            "status": "active",
            "schema_json": {"type": "object"},
        },
    )
    assert api_function_response.status_code == 201
    assert api_function_response.json()["http_method"] == "POST"

    list_response = client.get("/api/v1/api-functions", params={"pool_id": pool_id})
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
