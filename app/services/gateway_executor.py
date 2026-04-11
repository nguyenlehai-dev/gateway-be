from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import re
from time import perf_counter
from uuid import uuid4

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.security import mask_secret, resolve_gateway_key_context
from app.models.api_function import ApiFunction
from app.models.gateway_request import GatewayRequest
from app.models.pool import Pool
from app.models.pool_api_key import PoolApiKey
from app.schemas.google_genai import (
        GatewayExecuteOutput,
        GatewayExecuteRequest,
        GatewayExecuteResponse,
        GatewayJobStatusOutput,
        GatewayJobStatusResponse,
    GatewaySubmitRequest,
    GatewaySubmitResponse,
    GatewayUsage,
)
from app.services.google_genai_service import GoogleGenAIService, ProviderExecutionError
from app.services.provider_registry import ProviderRegistry


@dataclass
class ExecutionContext:
    function: ApiFunction
    pool: Pool
    vendor: object
    provider: object
    selected_pool_api_key: PoolApiKey | None
    provider_api_key: str
    project_number: str
    model: str


class GatewayExecutor:
    MODEL_ALIASES = {
        "google.genai.image_generation": GoogleGenAIService.image_model_aliases,
    }

    def __init__(self, db: Session):
        self.db = db
        self.provider_registry = ProviderRegistry()
        self.settings = get_settings()

    def execute(self, function_code: str, payload: GatewayExecuteRequest) -> GatewayExecuteResponse:
        if self._is_force_async_function(function_code):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Function '{function_code}' requires async submit. Use /submit and poll status.",
            )
        context = self._prepare_execution(function_code, payload, allow_direct_credentials=True)
        request_log = self._create_request_log(
            context,
            payload,
            status_value="processing",
            max_attempts=1,
            webhook_url=None,
        )
        return self._run_sync_execution(context, payload, request_log)

    def submit(self, function_code: str, payload: GatewaySubmitRequest) -> GatewaySubmitResponse:
        context = self._prepare_execution(function_code, payload, allow_direct_credentials=False)
        request_log = self._create_request_log(
            context,
            payload,
            status_value="queued",
            max_attempts=payload.max_attempts,
            webhook_url=str(payload.webhook_url) if payload.webhook_url else None,
        )
        self.db.commit()

        return GatewaySubmitResponse(
            request_id=request_log.request_id,
            status=request_log.status,
            function=context.function.code,
            poll_path=f"/api/v1/gateway/requests/{request_log.request_id}/status",
            webhook_url=str(payload.webhook_url) if payload.webhook_url else None,
        )

    def process_queued_request(self, request_id: str) -> GatewayJobStatusResponse:
        request_log = self._get_request_by_request_id(request_id)
        if request_log is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gateway request not found")
        return self._process_request_attempt(request_log)

    def retry_request(self, request_id: str) -> GatewayJobStatusResponse:
        request_log = self._get_request_by_request_id(request_id)
        if request_log is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gateway request not found")

        job_control = self._job_control(request_log)
        if not job_control.get("created_for_async"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Only async submitted jobs can be retried",
            )
        if request_log.status == "success":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Completed successful jobs do not need retry",
            )
        if request_log.status == "processing":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Job is currently processing",
            )
        if request_log.status == "queued":
            return self._build_status_response(request_log)

        max_attempts = int(job_control.get("max_attempts") or self.settings.async_job_default_max_attempts)
        manual_retry_count = int(job_control.get("manual_retry_count") or 0) + 1
        self._set_job_control(
            request_log,
            {
                **job_control,
                "retry_count": 0,
                "max_attempts": max_attempts,
                "next_retry_at": None,
                "completed_at": None,
                "manual_retry_count": manual_retry_count,
                "last_manual_retry_at": datetime.now(timezone.utc).isoformat(),
                "webhook_status": "pending" if job_control.get("webhook_url") else None,
                "webhook_last_error": None,
                "webhook_delivery": None,
            },
        )
        request_log.status = "queued"
        request_log.error_message = None
        request_log.provider_request_json = None
        request_log.provider_response_json = None
        request_log.output_text = None
        request_log.latency_ms = None
        self.db.commit()
        self.db.refresh(request_log)
        return self._build_status_response(request_log)

    def get_job_status(self, request_id: str) -> GatewayJobStatusResponse:
        request_log = self._get_request_by_request_id(request_id)
        if request_log is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gateway request not found")
        return self._build_status_response(request_log)

    def process_due_requests(self, limit: int | None = None) -> list[GatewayJobStatusResponse]:
        max_items = limit or self.settings.async_job_batch_size
        now = datetime.now(timezone.utc)
        stmt = (
            select(GatewayRequest)
            .options(
                joinedload(GatewayRequest.api_function).joinedload(ApiFunction.pool).joinedload(Pool.vendor),
                joinedload(GatewayRequest.pool).joinedload(Pool.vendor),
                joinedload(GatewayRequest.vendor),
                joinedload(GatewayRequest.selected_pool_api_key),
            )
            .where(GatewayRequest.status.in_(["queued", "retrying"]))
            .order_by(GatewayRequest.id.asc())
        )

        results: list[GatewayJobStatusResponse] = []
        for request_log in self.db.execute(stmt).scalars():
            next_retry_at = self._job_control(request_log).get("next_retry_at")
            next_retry_dt = self._parse_datetime(next_retry_at)
            if next_retry_dt is not None and next_retry_dt > now:
                continue
            results.append(self._process_request_attempt(request_log))
            if len(results) >= max_items:
                break
        return results

    def _process_request_attempt(self, request_log: GatewayRequest) -> GatewayJobStatusResponse:
        function = request_log.api_function
        pool = request_log.pool
        vendor = request_log.vendor
        selected_pool_api_key = request_log.selected_pool_api_key
        if function is None or pool is None or vendor is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gateway request context is missing")
        if selected_pool_api_key is None:
            request_log.status = "failed"
            request_log.error_message = "Async execution requires a managed Pool API key"
            self._mark_job_finished(request_log)
            self.db.commit()
            self._deliver_webhook_if_needed(request_log)
            return self._build_status_response(request_log)

        provider = self.provider_registry.resolve(vendor.code, function.provider_action)
        payload_json = request_log.payload_json or {}
        payload = GatewayExecuteRequest(
            api_key=selected_pool_api_key.provider_api_key,
            project_number=request_log.project_number,
            model=request_log.model,
            prompt=str(payload_json.get("prompt") or ""),
            input_images=list(payload_json.get("input_images") or []),
            aspect_ratio=payload_json.get("aspect_ratio"),
            image_size=payload_json.get("image_size"),
            references_image=list(payload_json.get("references_image") or []),
            references_video=list(payload_json.get("references_video") or []),
            references_audios=list(payload_json.get("references_audios") or []),
        )

        job_control = self._job_control(request_log)
        retry_count = int(job_control.get("retry_count") or 0)
        max_attempts = int(job_control.get("max_attempts") or self.settings.async_job_default_max_attempts)
        job_control["last_attempt_at"] = datetime.now(timezone.utc).isoformat()
        request_log.status = "processing"
        self._set_job_control(request_log, job_control)
        self.db.commit()

        started = perf_counter()
        try:
            (
                provider_request,
                provider_response,
                output_text,
                output_images,
            ) = self._execute_provider(
                function.provider_action,
                provider,
                payload,
                timeout_seconds=self.settings.provider_timeout_seconds,
                max_retries=self.settings.provider_max_retries,
            )
            latency_ms = int((perf_counter() - started) * 1000)

            request_log.provider_request_json = provider_request
            request_log.provider_response_json = provider_response
            request_log.output_text = output_text
            request_log.status = "success"
            request_log.error_message = None
            request_log.latency_ms = latency_ms
            selected_pool_api_key.last_used_at = datetime.now(timezone.utc)
            self._mark_job_finished(request_log)
            self.db.commit()
            self._deliver_webhook_if_needed(request_log)
            return self._build_status_response(request_log)
        except ProviderExecutionError as exc:
            latency_ms = int((perf_counter() - started) * 1000)
            request_log.provider_request_json = exc.provider_request
            request_log.provider_response_json = self._normalize_provider_response(exc.provider_response)
            request_log.error_message = exc.message
            request_log.latency_ms = latency_ms
            selected_pool_api_key.last_error_at = datetime.now(timezone.utc)

            is_retryable = self._is_retryable_provider_error(exc.provider_status_code)
            if is_retryable and retry_count + 1 < max_attempts:
                next_retry_at = self._compute_next_retry_at(
                    attempt_number=retry_count + 1,
                    provider_response=exc.provider_response,
                )
                request_log.status = "retrying"
                self._set_job_control(
                    request_log,
                    {
                        **job_control,
                        "retry_count": retry_count + 1,
                        "max_attempts": max_attempts,
                        "next_retry_at": next_retry_at.isoformat(),
                    },
                )
                request_log.provider_response_json = {
                    "job_retry": {
                        "attempt": retry_count + 1,
                        "max_attempts": max_attempts,
                        "next_retry_at": next_retry_at.isoformat(),
                        "provider_status_code": exc.provider_status_code,
                    },
                    "provider_error": self._normalize_provider_response(exc.provider_response),
                }
                self.db.commit()
                return self._build_status_response(request_log)

            request_log.status = "failed"
            self._set_job_control(
                request_log,
                {
                    **job_control,
                    "retry_count": retry_count + 1,
                    "max_attempts": max_attempts,
                    "next_retry_at": None,
                },
            )
            self._mark_job_finished(request_log)
            self.db.commit()
            self._deliver_webhook_if_needed(request_log)
            return self._build_status_response(request_log)

    def _prepare_execution(
        self,
        function_code: str,
        payload: GatewayExecuteRequest,
        *,
        allow_direct_credentials: bool,
    ) -> ExecutionContext:
        function = self.db.execute(
            select(ApiFunction)
            .options(joinedload(ApiFunction.pool).joinedload(Pool.vendor))
            .where(ApiFunction.code == function_code, ApiFunction.status == "active")
        ).scalar_one_or_none()

        if function is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API Function not found")

        pool = function.pool
        vendor = pool.vendor
        if pool.status != "active" or vendor.status != "active":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Vendor or Pool is inactive")

        provider = self.provider_registry.resolve(vendor.code, function.provider_action)
        config = pool.config_json or {}
        selected_pool_api_key: PoolApiKey | None = None

        if payload.gateway_api_key:
            gateway_key_context = resolve_gateway_key_context(self.db, payload.gateway_api_key)
            if gateway_key_context is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid gateway API key")
            if gateway_key_context.pool_id != pool.id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Gateway API key cannot access this pool")
            selected_pool_api_key = self._select_pool_api_key(pool.id)
            if selected_pool_api_key is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active API Keys are configured for this pool")
            provider_api_key = selected_pool_api_key.provider_api_key
            project_number = selected_pool_api_key.project_number
            model = self._resolve_model_name(
                function.provider_action,
                payload.model or config.get("default_model") or "gemini-2.5-flash",
            )
        else:
            if not allow_direct_credentials:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Async submit requires gateway_api_key or X-Gateway-Api-Key",
                )
            if not payload.api_key:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="api_key is required")
            if not payload.project_number:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="project_number is required")
            provider_api_key = payload.api_key
            project_number = payload.project_number
            model = self._resolve_model_name(function.provider_action, payload.model or "gemini-2.5-flash")

        return ExecutionContext(
            function=function,
            pool=pool,
            vendor=vendor,
            provider=provider,
            selected_pool_api_key=selected_pool_api_key,
            provider_api_key=provider_api_key,
            project_number=project_number,
            model=model,
        )

    def _create_request_log(
        self,
        context: ExecutionContext,
        payload: GatewayExecuteRequest,
        *,
        status_value: str,
        max_attempts: int,
        webhook_url: str | None,
    ) -> GatewayRequest:
        request_id = f"gw_{uuid4().hex[:12]}"
        masked_api_key = mask_secret(context.provider_api_key)
        payload_for_log = payload.model_dump()
        if payload_for_log.get("webhook_url") is not None:
            payload_for_log["webhook_url"] = str(payload_for_log["webhook_url"])
        payload_for_log["api_key"] = masked_api_key
        if payload.gateway_api_key:
            payload_for_log["gateway_api_key"] = mask_secret(payload.gateway_api_key)
        payload_for_log["project_number"] = context.project_number
        payload_for_log["model"] = context.model
        payload_for_log["job_control"] = {
            "retry_count": 0,
            "max_attempts": max_attempts,
            "next_retry_at": None,
            "webhook_url": webhook_url,
            "webhook_status": "pending" if webhook_url else None,
            "created_for_async": status_value != "processing",
        }

        request_log = GatewayRequest(
            vendor_id=context.pool.vendor_id,
            pool_id=context.pool.id,
            api_function_id=context.function.id,
            selected_pool_api_key_id=context.selected_pool_api_key.id if context.selected_pool_api_key is not None else None,
            request_id=request_id,
            model=context.model,
            project_number=context.project_number,
            api_key_masked=masked_api_key,
            payload_json=payload_for_log,
            status=status_value,
        )
        self.db.add(request_log)
        self.db.flush()
        return request_log

    def _run_sync_execution(
        self,
        context: ExecutionContext,
        payload: GatewayExecuteRequest,
        request_log: GatewayRequest,
    ) -> GatewayExecuteResponse:
        started = perf_counter()
        try:
            provider_payload = payload.model_copy(
                update={
                    "api_key": context.provider_api_key,
                    "project_number": context.project_number,
                    "model": context.model,
                }
            )
            (
                provider_request,
                provider_response,
                output_text,
                output_images,
            ) = self._execute_provider(
                context.function.provider_action,
                context.provider,
                provider_payload,
                timeout_seconds=self.settings.sync_provider_timeout_seconds,
                max_retries=self.settings.sync_provider_max_retries,
            )
            latency_ms = int((perf_counter() - started) * 1000)

            request_log.provider_request_json = provider_request
            request_log.provider_response_json = provider_response
            request_log.output_text = output_text
            request_log.status = "success"
            request_log.latency_ms = latency_ms
            if context.selected_pool_api_key is not None:
                context.selected_pool_api_key.last_used_at = datetime.now(timezone.utc)
            self._mark_job_finished(request_log)
            self.db.commit()

            usage_meta = provider_response.get("usageMetadata", {})
            return GatewayExecuteResponse(
                request_id=request_log.request_id,
                vendor=context.vendor.code,
                pool=context.pool.code,
                function=context.function.code,
                model=context.model,
                status="success",
                output=GatewayExecuteOutput(text=output_text, images=output_images),
                usage=GatewayUsage(
                    input_tokens=usage_meta.get("promptTokenCount"),
                    output_tokens=usage_meta.get("candidatesTokenCount"),
                    total_tokens=usage_meta.get("totalTokenCount"),
                ),
                latency_ms=latency_ms,
            )
        except ProviderExecutionError as exc:
            latency_ms = int((perf_counter() - started) * 1000)
            request_log.provider_request_json = exc.provider_request
            request_log.provider_response_json = self._normalize_provider_response(exc.provider_response)
            request_log.status = "failed"
            request_log.latency_ms = latency_ms
            request_log.error_message = exc.message
            if context.selected_pool_api_key is not None:
                context.selected_pool_api_key.last_error_at = datetime.now(timezone.utc)
            self._mark_job_finished(request_log)
            self.db.commit()
            response_status = self._map_provider_error_status(exc.provider_status_code)
            response_headers = {"X-Gateway-Request-Id": request_log.request_id}
            retry_after = self._extract_retry_after_seconds(exc.provider_response)
            if retry_after is not None:
                response_headers["Retry-After"] = str(retry_after)
            raise HTTPException(
                status_code=response_status,
                headers=response_headers,
                detail={
                    "message": "Google GenAI request failed",
                    "request_id": request_log.request_id,
                    "provider_status_code": exc.provider_status_code,
                    "provider_error": exc.provider_response if exc.provider_response is not None else exc.message,
                },
            ) from exc

    def _deliver_webhook_if_needed(self, request_log: GatewayRequest) -> None:
        job_control = self._job_control(request_log)
        webhook_url = job_control.get("webhook_url")
        if not webhook_url:
            return
        output_images = self._extract_images_from_provider_response(request_log.provider_response_json)

        delivery_meta: dict[str, object]
        try:
            response = httpx.post(
                str(webhook_url),
                json={
                    "request_id": request_log.request_id,
                    "status": request_log.status,
                    "model": request_log.model,
                    "output_text": request_log.output_text,
                    "output_images": [image.model_dump() for image in output_images],
                    "error_message": request_log.error_message,
                    "latency_ms": request_log.latency_ms,
                },
                timeout=self.settings.webhook_timeout_seconds,
            )
            response.raise_for_status()
            delivery_meta = {
                "status": "success",
                "response_status_code": response.status_code,
                "delivered_at": datetime.now(timezone.utc).isoformat(),
            }
            job_control["webhook_status"] = "success"
            job_control["webhook_last_error"] = None
        except httpx.HTTPError as exc:
            delivery_meta = {
                "status": "failed",
                "error": str(exc),
                "attempted_at": datetime.now(timezone.utc).isoformat(),
            }
            job_control["webhook_status"] = "failed"
            job_control["webhook_last_error"] = str(exc)

        job_control["webhook_delivery"] = delivery_meta
        self._set_job_control(request_log, job_control)
        self.db.commit()

    def _resolve_model_name(self, provider_action: str, model: str) -> str:
        aliases = self.MODEL_ALIASES.get(provider_action, {})
        normalized_model = model.strip()
        return aliases.get(normalized_model, normalized_model)

    def _get_request_by_request_id(self, request_id: str) -> GatewayRequest | None:
        return self.db.execute(
            select(GatewayRequest)
            .options(
                joinedload(GatewayRequest.api_function).joinedload(ApiFunction.pool).joinedload(Pool.vendor),
                joinedload(GatewayRequest.pool).joinedload(Pool.vendor),
                joinedload(GatewayRequest.vendor),
                joinedload(GatewayRequest.selected_pool_api_key),
            )
            .where(GatewayRequest.request_id == request_id)
        ).scalar_one_or_none()

    def _build_status_response(self, request_log: GatewayRequest) -> GatewayJobStatusResponse:
        function_code = request_log.api_function.code if request_log.api_function is not None else ""
        job_control = self._job_control(request_log)
        output_images = self._extract_images_from_provider_response(request_log.provider_response_json)
        return GatewayJobStatusResponse(
            request_id=request_log.request_id,
            function=function_code,
            status=request_log.status,
            model=request_log.model,
            output=GatewayJobStatusOutput(text=request_log.output_text, images=output_images),
            error_message=request_log.error_message,
            latency_ms=request_log.latency_ms,
            retry_count=int(job_control.get("retry_count") or 0),
            max_attempts=int(job_control.get("max_attempts") or 0),
            next_retry_at=self._parse_datetime(job_control.get("next_retry_at")),
            webhook_status=str(job_control.get("webhook_status")) if job_control.get("webhook_status") is not None else None,
        )

    def _mark_job_finished(self, request_log: GatewayRequest) -> None:
        job_control = self._job_control(request_log)
        job_control["next_retry_at"] = None
        job_control["completed_at"] = datetime.now(timezone.utc).isoformat()
        self._set_job_control(request_log, job_control)

    @staticmethod
    def _parse_datetime(value: object) -> datetime | None:
        if not isinstance(value, str) or not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    def _compute_next_retry_at(self, attempt_number: int, provider_response: dict | str | None) -> datetime:
        retry_after = self._extract_retry_after_seconds(provider_response)
        if retry_after is not None:
            delay = retry_after
        else:
            delay = self.settings.async_job_retry_base_delay_seconds * (2 ** max(attempt_number - 1, 0))
        delay = min(delay, self.settings.async_job_retry_max_delay_seconds)
        return datetime.now(timezone.utc) + timedelta(seconds=delay)

    @staticmethod
    def _job_control(request_log: GatewayRequest) -> dict:
        payload_json = dict(request_log.payload_json or {})
        job_control = payload_json.get("job_control")
        if isinstance(job_control, dict):
            return dict(job_control)
        return {}

    @staticmethod
    def _set_job_control(request_log: GatewayRequest, job_control: dict) -> None:
        payload_json = dict(request_log.payload_json or {})
        payload_json["job_control"] = job_control
        request_log.payload_json = payload_json

    def _select_pool_api_key(self, pool_id: int) -> PoolApiKey | None:
        stmt = (
            select(PoolApiKey)
            .where(PoolApiKey.pool_id == pool_id, PoolApiKey.status == "active")
            .order_by(PoolApiKey.priority.asc(), PoolApiKey.id.asc())
        )
        return self.db.execute(stmt).scalars().first()

    @staticmethod
    def _normalize_provider_response(provider_response: dict | str | None) -> dict | None:
        if isinstance(provider_response, dict):
            return provider_response
        if provider_response is not None:
            return {"raw": provider_response}
        return None

    @staticmethod
    def _is_retryable_provider_error(provider_status_code: int | None) -> bool:
        return provider_status_code in {429, 502, 503, 504} or provider_status_code is None

    @staticmethod
    def _map_provider_error_status(provider_status_code: int | None) -> int:
        if provider_status_code in {429, 503, 504}:
            return provider_status_code
        return status.HTTP_502_BAD_GATEWAY

    @staticmethod
    def _extract_retry_after_seconds(provider_response: dict | str | None) -> int | None:
        if not isinstance(provider_response, dict):
            return None

        error = provider_response.get("error")
        if not isinstance(error, dict):
            return None

        details = error.get("details")
        if isinstance(details, list):
            for item in details:
                if not isinstance(item, dict):
                    continue
                retry_delay = item.get("retryDelay")
                seconds = GatewayExecutor._parse_retry_delay_value(retry_delay)
                if seconds is not None:
                    return seconds

        message = error.get("message")
        return GatewayExecutor._parse_retry_delay_value(message)

    @staticmethod
    def _parse_retry_delay_value(value: object) -> int | None:
        if not isinstance(value, str):
            return None

        match = re.search(r"(\d+)(?:\.\d+)?s\b", value)
        if match:
            return max(1, int(match.group(1)))

        match = re.search(r"retry in (\d+)(?:\.\d+)?s", value, re.IGNORECASE)
        if match:
            return max(1, int(match.group(1)))

        return None

    @staticmethod
    def _execute_provider(
        provider_action: str,
        provider: object,
        payload: GatewayExecuteRequest,
        *,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
    ) -> tuple[dict, dict, str | None, list]:
        if provider_action == "google.genai.image_generation":
            provider_request, provider_response, output_text, output_images = provider.generate_image(
                payload,
                timeout_seconds=timeout_seconds,
                max_retries=max_retries,
            )
            return provider_request, provider_response, output_text, output_images

        provider_request, provider_response, output_text = provider.generate_text(
            payload,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )
        return provider_request, provider_response, output_text, []

    def _is_force_async_function(self, function_code: str) -> bool:
        raw = self.settings.sync_force_async_functions
        if not raw:
            return False
        items = {item.strip() for item in raw.split(",") if item.strip()}
        return function_code in items

    @staticmethod
    def _extract_images_from_provider_response(provider_response: dict | None) -> list:
        if not isinstance(provider_response, dict):
            return []
        parts = (
            provider_response.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [])
        )
        if not isinstance(parts, list):
            return []

        images = []
        for part in parts:
            if not isinstance(part, dict):
                continue
            inline_data = part.get("inline_data") or part.get("inlineData")
            if not isinstance(inline_data, dict):
                continue
            data = inline_data.get("data")
            if not data:
                continue
            mime_type = inline_data.get("mime_type") or inline_data.get("mimeType")
            images.append({"mime_type": mime_type, "data_base64": data})
        return images
