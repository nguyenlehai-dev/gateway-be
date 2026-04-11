from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_up() -> None:
    response = client.get("/up")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "gateway-be"}


def test_openapi_docs_path() -> None:
    response = client.get("/api/v1/openapi.json")

    assert response.status_code == 200
    body = response.json()
    assert body["info"]["title"] == "Gateway Backend"
