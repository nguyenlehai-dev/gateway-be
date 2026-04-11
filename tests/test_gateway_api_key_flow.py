from datetime import datetime, timedelta, timezone
from uuid import uuid4
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import and_, select

from app.db.session import SessionLocal
from app.models.api_function import ApiFunction
from app.models.gateway_api_key import GatewayApiKey
from app.models.gateway_request import GatewayRequest
from app.models.pool import Pool
from app.models.pool_api_key import PoolApiKey
from app.models.user import User
from app.models.vendor import Vendor
from app.main import app
from app.core.security import mask_secret
from app.services.gateway_executor import GatewayExecutor
from app.services.auth_service import hash_password, hash_secret


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


def test_verify_and_execute_with_gateway_api_key() -> None:
    suffix = uuid4().hex[:8]
    gateway_api_key = f"gwk_test_{suffix}_1234567890"
    function_code = f"text-generation-gwk-{suffix}"
    db = SessionLocal()
    try:
        vendor = db.execute(select(Vendor).where(Vendor.code == "google")).scalar_one_or_none()
        if vendor is None:
            vendor = Vendor(
                name="Google",
                slug="google",
                code="google",
                description="Vendor gateway key",
                status="active",
            )
            db.add(vendor)
            db.flush()

        pool = db.execute(
            select(Pool).where(and_(Pool.vendor_id == vendor.id, Pool.code == f"gemini-gwk-{suffix}"))
        ).scalar_one_or_none()
        if pool is None:
            pool = Pool(
                vendor_id=vendor.id,
                name=f"Gemini GWK {suffix}",
                slug=f"gemini-gwk-{suffix}",
                code=f"gemini-gwk-{suffix}",
                description="Pool gateway key",
                status="active",
                config_json={"provider": "google", "timeout_seconds": 60, "default_model": "gemini-3-flash-preview"},
            )
            db.add(pool)
            db.flush()

        customer = db.execute(
            select(User).where(and_(User.pool_id == pool.id, User.username == f"customer-{suffix}"))
        ).scalar_one_or_none()
        if customer is None:
            customer = User(
                username=f"customer-{suffix}",
                email=f"customer-{suffix}@gateway.test",
                full_name=f"Customer {suffix}",
                password_hash=hash_password("CustomerPass123"),
                role="customer",
                status="active",
                pool_id=pool.id,
            )
            db.add(customer)
            db.flush()

        pool_api_key = db.execute(
            select(PoolApiKey).where(and_(PoolApiKey.pool_id == pool.id, PoolApiKey.name == f"Primary Key {suffix}"))
        ).scalar_one_or_none()
        if pool_api_key is None:
            pool_api_key = PoolApiKey(
                pool_id=pool.id,
                name=f"Primary Key {suffix}",
                provider_api_key="AIzaSyDemoKey1234567890",
                provider_api_key_masked=mask_secret("AIzaSyDemoKey1234567890"),
                project_number="123456789",
                status="active",
                priority=100,
            )
            db.add(pool_api_key)
            db.flush()

        gw_api_key = db.execute(
            select(GatewayApiKey).where(and_(GatewayApiKey.pool_id == pool.id, GatewayApiKey.name == "Automated Test Key"))
        ).scalar_one_or_none()
        if gw_api_key is None:
            gw_api_key = GatewayApiKey(
                user_id=customer.id,
                pool_id=pool.id,
                name="Automated Test Key",
                key_hash=hash_secret(gateway_api_key),
                key_masked=mask_secret(gateway_api_key),
                status="active",
            )
            db.add(gw_api_key)
            db.flush()

        api_function = db.execute(
            select(ApiFunction).where(and_(ApiFunction.pool_id == pool.id, ApiFunction.code == function_code))
        ).scalar_one_or_none()
        if api_function is None:
            api_function = ApiFunction(
                pool_id=pool.id,
                name=f"Text Generation GWK {suffix}",
                code=function_code,
                description="Function gateway key",
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

    verify_response = client.post("/api/v1/gateway-keys/verify", json={"gateway_api_key": gateway_api_key})
    assert verify_response.status_code == 200
    verify_body = verify_response.json()
    assert verify_body["gateway_key_name"] == "Automated Test Key"
    assert verify_body["default_model"] == "gemini-3-flash-preview"

    list_vendors_response = client.get("/api/v1/vendors", headers={"X-Gateway-Api-Key": gateway_api_key})
    assert list_vendors_response.status_code == 200
    assert list_vendors_response.json()["total"] == 1

    with patch("app.services.google_genai_service.genai") as mock_genai:
        mock_genai.GenerativeModel.return_value.generate_content.return_value.to_dict.return_value = _mock_text_response(
            "Generated from gateway key",
            input_tokens=11,
            output_tokens=21,
            total_tokens=32,
        )

        execute_response = client.post(
            f"/api/v1/gateway/functions/{function_code}/execute",
            headers={"X-Gateway-Api-Key": gateway_api_key},
            json={
                "prompt": "Hello from gateway key",
                "references_image": [],
                "references_video": [],
                "references_audios": [],
            },
        )

    assert execute_response.status_code == 200
    execute_body = execute_response.json()
    assert execute_body["status"] == "success"
    assert execute_body["model"] == "gemini-3-flash-preview"
    assert execute_body["output"]["text"] == "Generated from gateway key"


def test_submit_and_poll_with_gateway_api_key() -> None:
    suffix = uuid4().hex[:8]
    gateway_api_key = f"gwk_async_{suffix}_1234567890"
    function_code = f"text-generation-submit-{suffix}"
    db = SessionLocal()
    try:
        vendor = db.execute(select(Vendor).where(Vendor.code == "google")).scalar_one_or_none()
        if vendor is None:
            vendor = Vendor(
                name="Google",
                slug="google",
                code="google",
                description="Vendor gateway key",
                status="active",
            )
            db.add(vendor)
            db.flush()

        pool = Pool(
            vendor_id=vendor.id,
            name=f"Gemini Submit {suffix}",
            slug=f"gemini-submit-{suffix}",
            code=f"gemini-submit-{suffix}",
            description="Pool submit",
            status="active",
            config_json={"provider": "google", "timeout_seconds": 60, "default_model": "gemini-3-flash-preview"},
        )
        db.add(pool)
        db.flush()

        customer = User(
            username=f"submit-customer-{suffix}",
            email=f"submit-customer-{suffix}@gateway.test",
            full_name=f"Submit Customer {suffix}",
            password_hash=hash_password("CustomerPass123"),
            role="customer",
            status="active",
            pool_id=pool.id,
        )
        db.add(customer)
        db.flush()

        pool_api_key = PoolApiKey(
            pool_id=pool.id,
            name=f"Submit Key {suffix}",
            provider_api_key="AIzaSyDemoKey1234567890",
            provider_api_key_masked=mask_secret("AIzaSyDemoKey1234567890"),
            project_number="123456789",
            status="active",
            priority=100,
        )
        db.add(pool_api_key)
        db.flush()

        gw_api_key = GatewayApiKey(
            user_id=customer.id,
            pool_id=pool.id,
            name=f"Submit GWK {suffix}",
            key_hash=hash_secret(gateway_api_key),
            key_masked=mask_secret(gateway_api_key),
            status="active",
        )
        db.add(gw_api_key)
        db.flush()

        api_function = ApiFunction(
            pool_id=pool.id,
            name=f"Text Generation Submit {suffix}",
            code=function_code,
            description="Function submit",
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
            "Generated async from gateway key",
            input_tokens=12,
            output_tokens=22,
            total_tokens=34,
        )

        submit_response = client.post(
            f"/api/v1/gateway/functions/{function_code}/submit",
            headers={"X-Gateway-Api-Key": gateway_api_key},
            json={
                "prompt": "Hello from async gateway key",
                "references_image": [],
                "references_video": [],
                "references_audios": [],
                "max_attempts": 2,
            },
        )

    assert submit_response.status_code == 202
    submit_body = submit_response.json()
    assert submit_body["function"] == function_code
    assert submit_body["status"] == "queued"

    request_id = submit_body["request_id"]
    status_response = client.get(
        f"/api/v1/gateway/requests/{request_id}/status",
        headers={"X-Gateway-Api-Key": gateway_api_key},
    )

    assert status_response.status_code == 200
    status_body = status_response.json()
    assert status_body["request_id"] == request_id
    assert status_body["status"] == "success"
    assert status_body["output"]["text"] == "Generated async from gateway key"


def test_submit_retry_then_runner_processes_due_job() -> None:
    suffix = uuid4().hex[:8]
    gateway_api_key = f"gwk_retry_{suffix}_1234567890"
    function_code = f"text-generation-retry-{suffix}"
    db = SessionLocal()
    try:
        vendor = db.execute(select(Vendor).where(Vendor.code == "google")).scalar_one_or_none()
        if vendor is None:
            vendor = Vendor(
                name="Google",
                slug="google",
                code="google",
                description="Vendor retry",
                status="active",
            )
            db.add(vendor)
            db.flush()

        pool = Pool(
            vendor_id=vendor.id,
            name=f"Gemini Retry {suffix}",
            slug=f"gemini-retry-{suffix}",
            code=f"gemini-retry-{suffix}",
            description="Pool retry",
            status="active",
            config_json={"provider": "google", "timeout_seconds": 60, "default_model": "gemini-3-flash-preview"},
        )
        db.add(pool)
        db.flush()

        customer = User(
            username=f"retry-customer-{suffix}",
            email=f"retry-customer-{suffix}@gateway.test",
            full_name=f"Retry Customer {suffix}",
            password_hash=hash_password("CustomerPass123"),
            role="customer",
            status="active",
            pool_id=pool.id,
        )
        db.add(customer)
        db.flush()

        pool_api_key = PoolApiKey(
            pool_id=pool.id,
            name=f"Retry Key {suffix}",
            provider_api_key="AIzaSyDemoKey1234567890",
            provider_api_key_masked=mask_secret("AIzaSyDemoKey1234567890"),
            project_number="123456789",
            status="active",
            priority=100,
        )
        db.add(pool_api_key)
        db.flush()

        gw_api_key = GatewayApiKey(
            user_id=customer.id,
            pool_id=pool.id,
            name=f"Retry GWK {suffix}",
            key_hash=hash_secret(gateway_api_key),
            key_masked=mask_secret(gateway_api_key),
            status="active",
        )
        db.add(gw_api_key)
        db.flush()

        api_function = ApiFunction(
            pool_id=pool.id,
            name=f"Text Generation Retry {suffix}",
            code=function_code,
            description="Function retry",
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

    first_request = httpx.Request("POST", "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent")
    first_response = httpx.Response(
        503,
        request=first_request,
        json={"error": {"code": 503, "message": "This model is currently experiencing high demand."}},
    )
    first_exc = httpx.HTTPStatusError("503", request=first_request, response=first_response)
    second_exc = httpx.HTTPStatusError("503", request=first_request, response=first_response)

    with patch("app.services.google_genai_service.genai") as mock_genai:
        success_response = type("Resp", (), {})()
        success_response.to_dict = lambda: _mock_text_response(
            "Recovered after retry",
            input_tokens=12,
            output_tokens=22,
            total_tokens=34,
        )
        mock_genai.GenerativeModel.return_value.generate_content.side_effect = [first_exc, second_exc, success_response]

        submit_response = client.post(
            f"/api/v1/gateway/functions/{function_code}/submit",
            headers={"X-Gateway-Api-Key": gateway_api_key},
            json={
                "prompt": "Retry me",
                "references_image": [],
                "references_video": [],
                "references_audios": [],
                "max_attempts": 3,
            },
        )

        assert submit_response.status_code == 202
        request_id = submit_response.json()["request_id"]

        status_response = client.get(
            f"/api/v1/gateway/requests/{request_id}/status",
            headers={"X-Gateway-Api-Key": gateway_api_key},
        )
        assert status_response.status_code == 200
        status_body = status_response.json()
        assert status_body["status"] == "retrying"
        assert status_body["retry_count"] == 1

        db = SessionLocal()
        try:
            entity = db.execute(select(GatewayRequest).where(GatewayRequest.request_id == request_id)).scalar_one()
            payload_json = dict(entity.payload_json)
            payload_json["job_control"]["next_retry_at"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
            entity.payload_json = payload_json
            db.commit()

            executor = GatewayExecutor(db)
            processed = executor.process_queued_request(request_id)
            assert processed.request_id == request_id
        finally:
            db.close()

    final_status = client.get(
        f"/api/v1/gateway/requests/{request_id}/status",
        headers={"X-Gateway-Api-Key": gateway_api_key},
    )
    assert final_status.status_code == 200
    final_body = final_status.json()
    assert final_body["status"] == "success"
    assert final_body["retry_count"] == 1
    assert final_body["output"]["text"] == "Recovered after retry"


def test_submit_with_webhook_marks_delivery_success() -> None:
    suffix = uuid4().hex[:8]
    gateway_api_key = f"gwk_webhook_{suffix}_1234567890"
    function_code = f"text-generation-webhook-{suffix}"
    db = SessionLocal()
    try:
        vendor = db.execute(select(Vendor).where(Vendor.code == "google")).scalar_one_or_none()
        if vendor is None:
            vendor = Vendor(
                name="Google",
                slug="google",
                code="google",
                description="Vendor webhook",
                status="active",
            )
            db.add(vendor)
            db.flush()

        pool = Pool(
            vendor_id=vendor.id,
            name=f"Gemini Webhook {suffix}",
            slug=f"gemini-webhook-{suffix}",
            code=f"gemini-webhook-{suffix}",
            description="Pool webhook",
            status="active",
            config_json={"provider": "google", "timeout_seconds": 60, "default_model": "gemini-3-flash-preview"},
        )
        db.add(pool)
        db.flush()

        customer = User(
            username=f"webhook-customer-{suffix}",
            email=f"webhook-customer-{suffix}@gateway.test",
            full_name=f"Webhook Customer {suffix}",
            password_hash=hash_password("CustomerPass123"),
            role="customer",
            status="active",
            pool_id=pool.id,
        )
        db.add(customer)
        db.flush()

        pool_api_key = PoolApiKey(
            pool_id=pool.id,
            name=f"Webhook Key {suffix}",
            provider_api_key="AIzaSyDemoKey1234567890",
            provider_api_key_masked=mask_secret("AIzaSyDemoKey1234567890"),
            project_number="123456789",
            status="active",
            priority=100,
        )
        db.add(pool_api_key)
        db.flush()

        gw_api_key = GatewayApiKey(
            user_id=customer.id,
            pool_id=pool.id,
            name=f"Webhook GWK {suffix}",
            key_hash=hash_secret(gateway_api_key),
            key_masked=mask_secret(gateway_api_key),
            status="active",
        )
        db.add(gw_api_key)
        db.flush()

        api_function = ApiFunction(
            pool_id=pool.id,
            name=f"Text Generation Webhook {suffix}",
            code=function_code,
            description="Function webhook",
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

    def mocked_httpx_post(url: str, *args, **kwargs):
        assert url == "https://example.com/callback"
        response = type("WebhookResp", (), {})()
        response.raise_for_status = lambda: None
        response.status_code = 200
        return response

    with patch("app.services.google_genai_service.genai") as mock_genai, patch(
        "app.services.gateway_executor.httpx.post", side_effect=mocked_httpx_post
    ):
        mock_genai.GenerativeModel.return_value.generate_content.return_value.to_dict.return_value = _mock_text_response(
            "Generated with webhook"
        )

        submit_response = client.post(
            f"/api/v1/gateway/functions/{function_code}/submit",
            headers={"X-Gateway-Api-Key": gateway_api_key},
            json={
                "prompt": "Webhook me",
                "references_image": [],
                "references_video": [],
                "references_audios": [],
                "max_attempts": 2,
                "webhook_url": "https://example.com/callback",
            },
        )

    assert submit_response.status_code == 202
    request_id = submit_response.json()["request_id"]

    status_response = client.get(
        f"/api/v1/gateway/requests/{request_id}/status",
        headers={"X-Gateway-Api-Key": gateway_api_key},
    )
    assert status_response.status_code == 200
    status_body = status_response.json()
    assert status_body["status"] == "success"
    assert status_body["webhook_status"] == "success"


def test_manual_retry_endpoint_requeues_failed_job() -> None:
    suffix = uuid4().hex[:8]
    gateway_api_key = f"gwk_manual_retry_{suffix}_1234567890"
    function_code = f"text-generation-manual-retry-{suffix}"
    db = SessionLocal()
    try:
        vendor = db.execute(select(Vendor).where(Vendor.code == "google")).scalar_one_or_none()
        if vendor is None:
            vendor = Vendor(
                name="Google",
                slug="google",
                code="google",
                description="Vendor manual retry",
                status="active",
            )
            db.add(vendor)
            db.flush()

        pool = Pool(
            vendor_id=vendor.id,
            name=f"Gemini Manual Retry {suffix}",
            slug=f"gemini-manual-retry-{suffix}",
            code=f"gemini-manual-retry-{suffix}",
            description="Pool manual retry",
            status="active",
            config_json={"provider": "google", "timeout_seconds": 60, "default_model": "gemini-3-flash-preview"},
        )
        db.add(pool)
        db.flush()

        customer = User(
            username=f"manual-retry-customer-{suffix}",
            email=f"manual-retry-customer-{suffix}@gateway.test",
            full_name=f"Manual Retry Customer {suffix}",
            password_hash=hash_password("CustomerPass123"),
            role="customer",
            status="active",
            pool_id=pool.id,
        )
        db.add(customer)
        db.flush()

        pool_api_key = PoolApiKey(
            pool_id=pool.id,
            name=f"Manual Retry Key {suffix}",
            provider_api_key="AIzaSyDemoKey1234567890",
            provider_api_key_masked=mask_secret("AIzaSyDemoKey1234567890"),
            project_number="123456789",
            status="active",
            priority=100,
        )
        db.add(pool_api_key)
        db.flush()

        gw_api_key = GatewayApiKey(
            user_id=customer.id,
            pool_id=pool.id,
            name=f"Manual Retry GWK {suffix}",
            key_hash=hash_secret(gateway_api_key),
            key_masked=mask_secret(gateway_api_key),
            status="active",
        )
        db.add(gw_api_key)
        db.flush()

        api_function = ApiFunction(
            pool_id=pool.id,
            name=f"Text Generation Manual Retry {suffix}",
            code=function_code,
            description="Function manual retry",
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

    first_request = httpx.Request("POST", "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent")
    first_response = httpx.Response(
        502,
        request=first_request,
        json={"error": {"code": 502, "message": "Bad Gateway"}},
    )
    first_exc = httpx.HTTPStatusError("502", request=first_request, response=first_response)

    with patch("app.services.google_genai_service.genai") as mock_genai:
        success_response = type("Resp", (), {})()
        success_response.to_dict = lambda: _mock_text_response(
            "Recovered after manual retry",
            input_tokens=12,
            output_tokens=22,
            total_tokens=34,
        )
        mock_genai.GenerativeModel.return_value.generate_content.side_effect = [first_exc, success_response]

        submit_response = client.post(
            f"/api/v1/gateway/functions/{function_code}/submit",
            headers={"X-Gateway-Api-Key": gateway_api_key},
            json={
                "prompt": "Retry me manually",
                "references_image": [],
                "references_video": [],
                "references_audios": [],
                "max_attempts": 1,
            },
        )

        assert submit_response.status_code == 202
        request_id = submit_response.json()["request_id"]

        failed_status = client.get(
            f"/api/v1/gateway/requests/{request_id}/status",
            headers={"X-Gateway-Api-Key": gateway_api_key},
        )
        assert failed_status.status_code == 200
        assert failed_status.json()["status"] == "failed"

        retry_response = client.post(
            f"/api/v1/gateway/requests/{request_id}/retry",
            headers={"X-Gateway-Api-Key": gateway_api_key},
        )

    assert retry_response.status_code == 200
    retry_body = retry_response.json()
    assert retry_body["request_id"] == request_id
    assert retry_body["status"] == "queued"

    final_status = client.get(
        f"/api/v1/gateway/requests/{request_id}/status",
        headers={"X-Gateway-Api-Key": gateway_api_key},
    )
    assert final_status.status_code == 200
    final_body = final_status.json()
    assert final_body["status"] == "success"
    assert final_body["output"]["text"] == "Recovered after manual retry"
