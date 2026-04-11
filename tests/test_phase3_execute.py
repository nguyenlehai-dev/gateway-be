from uuid import uuid4
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import and_, select

from app.db.session import SessionLocal
from app.models.api_function import ApiFunction
from app.models.pool import Pool
from app.models.vendor import Vendor
from app.main import app
from app.schemas.google_genai import GatewayExecuteRequest
from app.services.google_genai_service import GoogleGenAIService


client = TestClient(app)


def _mock_text_response(text: str, *, input_tokens: int = 10, output_tokens: int = 20, total_tokens: int = 30) -> dict:
    return {
        "candidates": [{"content": {"parts": [{"text": text}]}}],
        "usageMetadata": {
            "promptTokenCount": input_tokens,
            "candidatesTokenCount": output_tokens,
            "totalTokenCount": total_tokens,
        },
    }


def test_execute_text_generation() -> None:
    suffix = uuid4().hex[:8]
    function_code = f"text-generation-{suffix}"
    db = SessionLocal()
    try:
        vendor = db.execute(select(Vendor).where(Vendor.code == "google")).scalar_one_or_none()
        if vendor is None:
            vendor = Vendor(
                name="Google",
                slug="google",
                code="google",
                description="Vendor execute",
                status="active",
            )
            db.add(vendor)
            db.flush()

        pool = db.execute(
            select(Pool).where(and_(Pool.vendor_id == vendor.id, Pool.code == f"gemini-execute-{suffix}"))
        ).scalar_one_or_none()
        if pool is None:
            pool = Pool(
                vendor_id=vendor.id,
                name=f"Gemini Execute {suffix}",
                slug=f"gemini-execute-{suffix}",
                code=f"gemini-execute-{suffix}",
                description="Pool execute",
                status="active",
                config_json={"timeout_seconds": 60},
            )
            db.add(pool)
            db.flush()

        api_function = ApiFunction(
            pool_id=pool.id,
            name=f"Text Generation Execute {suffix}",
            code=function_code,
            description="Function execute",
            http_method="POST",
            path=f"/api/v1/gateway/functions/{function_code}/execute",
            provider_action="google.genai.text_generation",
            status="active",
            schema_json={"type": "object"},
        )
        db.add(api_function)
        db.commit()
    finally:
        db.close()

    with patch("app.services.google_genai_service.genai") as mock_genai:
        mock_genai.GenerativeModel.return_value.generate_content.return_value.to_dict.return_value = _mock_text_response(
            "Generated text from Gemini"
        )

        response = client.post(
            f"/api/v1/gateway/functions/{function_code}/execute",
            json={
                "api_key": "AIzaSyDemoKey1234567890",
                "project_number": "123456789",
                "model": "gemini-2.5-flash",
                "prompt": "Hello Gemini",
                "references_image": ["https://example.com/a.png"],
                "references_video": [],
                "references_audios": [],
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["function"] == function_code
    assert body["output"]["text"] == "Generated text from Gemini"
    assert body["output"]["images"] == []
    assert body["usage"]["total_tokens"] == 30
    mock_genai.configure.assert_called_once_with(api_key="AIzaSyDemoKey1234567890")
    mock_genai.GenerativeModel.assert_called_once_with("gemini-2.5-flash")
    _, generate_kwargs = mock_genai.GenerativeModel.return_value.generate_content.call_args
    assert generate_kwargs["safety_settings"][0]["threshold"] == "BLOCK_NONE"
    assert generate_kwargs["request_options"] == {"timeout": 300.0}


def test_text_generation_sdk_retries_provider_timeout() -> None:
    service = GoogleGenAIService()
    payload = GatewayExecuteRequest(
        api_key="AIzaSyDemoKey1234567890",
        model="gemini-2.5-flash",
        prompt="Generate a script",
    )
    provider_request = service.build_text_sdk_request(payload)
    success_response = type("Resp", (), {})()
    success_response.to_dict = lambda: _mock_text_response("Recovered after timeout")

    with patch("app.services.google_genai_service.sleep"), patch("app.services.google_genai_service.genai") as mock_genai:
        mock_genai.GenerativeModel.return_value.generate_content.side_effect = [
            Exception("504 The request timed out. Please try again."),
            success_response,
        ]

        provider_response = service._generate_text_with_sdk(
            payload,
            provider_request,
            timeout_seconds=60,
            max_retries=1,
        )

    assert service._extract_text(service._extract_parts(provider_response)) == "Recovered after timeout"
    assert mock_genai.GenerativeModel.return_value.generate_content.call_count == 2
    _, generate_kwargs = mock_genai.GenerativeModel.return_value.generate_content.call_args
    assert generate_kwargs["request_options"] == {"timeout": 300.0}


def test_execute_image_generation() -> None:
    suffix = uuid4().hex[:8]
    function_code = f"image-generation-{suffix}"
    db = SessionLocal()
    try:
        vendor = db.execute(select(Vendor).where(Vendor.code == "google")).scalar_one_or_none()
        if vendor is None:
            vendor = Vendor(
                name="Google",
                slug="google",
                code="google",
                description="Vendor image",
                status="active",
            )
            db.add(vendor)
            db.flush()

        pool = db.execute(
            select(Pool).where(and_(Pool.vendor_id == vendor.id, Pool.code == f"image-gen-{suffix}"))
        ).scalar_one_or_none()
        if pool is None:
            pool = Pool(
                vendor_id=vendor.id,
                name=f"Image Gen {suffix}",
                slug=f"image-gen-{suffix}",
                code=f"image-gen-{suffix}",
                description="Pool image",
                status="active",
                config_json={"timeout_seconds": 60},
            )
            db.add(pool)
            db.flush()

        api_function = ApiFunction(
            pool_id=pool.id,
            name=f"Image Generation Execute {suffix}",
            code=function_code,
            description="Function image",
            http_method="POST",
            path=f"/api/v1/gateway/functions/{function_code}/execute",
            provider_action="google.genai.image_generation",
            status="active",
            schema_json={"type": "object"},
        )
        db.add(api_function)
        db.commit()
    finally:
        db.close()

    with patch("app.services.google_genai_service.httpx.post") as mock_post:
        mock_post.return_value.raise_for_status.return_value = None
        mock_post.return_value.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "inline_data": {
                                    "mime_type": "image/png",
                                    "data": "ZmFrZV9pbWFnZQ==",
                                }
                            }
                        ]
                    }
                }
            ]
        }

        response = client.post(
            f"/api/v1/gateway/functions/{function_code}/execute",
            json={
                "api_key": "AIzaSyDemoKey1234567890",
                "project_number": "123456789",
                "model": "nano-banana-2",
                "prompt": "Generate a poster",
                "input_images": [],
                "aspect_ratio": "16:9",
                "image_size": "1K",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["function"] == function_code
    assert body["model"] == "gemini-3.1-flash-image-preview"
    assert body["output"]["text"] is None
    assert body["output"]["images"][0]["data_base64"] == "ZmFrZV9pbWFnZQ=="
    request_kwargs = mock_post.call_args.kwargs
    assert request_kwargs["json"]["generation_config"]["response_modalities"] == ["TEXT", "IMAGE"]
    assert request_kwargs["json"]["generation_config"]["image_config"] == {
        "aspect_ratio": "16:9",
        "image_size": "1K",
    }
    assert mock_post.call_args.args[0].endswith("/models/gemini-3.1-flash-image-preview:generateContent")
