import re
from time import sleep
from typing import Any

import httpx
try:
    import google.generativeai as genai
except ImportError:  # pragma: no cover - exercised only when dependency is missing at runtime
    genai = None

from app.core.config import get_settings
from app.schemas.google_genai import GatewayExecuteRequest, ImageOutput


class ProviderExecutionError(Exception):
    def __init__(
        self,
        *,
        message: str,
        provider_request: dict,
        provider_response: dict | str | None = None,
        provider_status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.provider_request = provider_request
        self.provider_response = provider_response
        self.provider_status_code = provider_status_code


class GoogleGenAIService:
    """Google GenAI integration for text and image generation."""

    base_url = "https://generativelanguage.googleapis.com/v1beta"
    text_min_timeout_seconds = 300.0
    sdk_retry_status_codes = {429, 503, 504}
    text_safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]
    image_model_aliases = {
        "nano-banana-2": "gemini-3.1-flash-image-preview",
        "nano-banana-pro": "gemini-3-pro-image-preview",
    }

    def build_text_contents(self, payload: GatewayExecuteRequest) -> str:
        sections = [payload.prompt]

        if payload.references_image:
            sections.append("Reference images:\n" + "\n".join(payload.references_image))
        if payload.references_video:
            sections.append("Reference videos:\n" + "\n".join(payload.references_video))
        if payload.references_audios:
            sections.append("Reference audios:\n" + "\n".join(payload.references_audios))

        return "\n\n".join(sections)

    def build_text_request(self, payload: GatewayExecuteRequest) -> dict:
        parts: list[dict] = [{"text": payload.prompt}]

        if payload.references_image:
            parts.append({"text": "Reference images:\n" + "\n".join(payload.references_image)})
        if payload.references_video:
            parts.append({"text": "Reference videos:\n" + "\n".join(payload.references_video)})
        if payload.references_audios:
            parts.append({"text": "Reference audios:\n" + "\n".join(payload.references_audios)})

        return {"contents": [{"parts": parts}]}

    def build_text_sdk_request(self, payload: GatewayExecuteRequest) -> dict:
        return {
            "sdk": "google-generativeai",
            "model": payload.model,
            "contents": self.build_text_contents(payload),
            "safety_settings": self.text_safety_settings,
        }

    def build_image_request(self, payload: GatewayExecuteRequest) -> dict:
        parts: list[dict] = [{"text": payload.prompt}]
        for image in payload.input_images:
            parts.append(
                {
                    "inline_data": {
                        "mime_type": image.mime_type,
                        "data": image.data_base64,
                    }
                }
            )

        request: dict = {
            "contents": [{"parts": parts}],
            "generation_config": {"response_modalities": ["TEXT", "IMAGE"]},
        }
        image_config: dict[str, str] = {}
        if payload.aspect_ratio:
            image_config["aspect_ratio"] = payload.aspect_ratio
        if payload.image_size:
            image_config["image_size"] = payload.image_size
        if image_config:
            request["generation_config"]["image_config"] = image_config
        return request

    @staticmethod
    def _get_response_text(response: Any) -> str:
        try:
            text = response.text
        except Exception:
            text = None
        return str(text or "").strip()

    @staticmethod
    def _get_usage_metadata(response: Any) -> dict:
        usage = getattr(response, "usage_metadata", None)
        if usage is None:
            return {}
        if isinstance(usage, dict):
            return {
                "promptTokenCount": usage.get("promptTokenCount") or usage.get("prompt_token_count"),
                "candidatesTokenCount": usage.get("candidatesTokenCount") or usage.get("candidates_token_count"),
                "totalTokenCount": usage.get("totalTokenCount") or usage.get("total_token_count"),
            }
        return {
            "promptTokenCount": getattr(usage, "prompt_token_count", None),
            "candidatesTokenCount": getattr(usage, "candidates_token_count", None),
            "totalTokenCount": getattr(usage, "total_token_count", None),
        }

    def _normalize_text_sdk_response(self, response: Any) -> dict:
        if hasattr(response, "to_dict"):
            try:
                raw = response.to_dict()
                if isinstance(raw, dict):
                    return raw
            except Exception:
                pass

        text_output = self._get_response_text(response)
        return {
            "candidates": [{"content": {"parts": [{"text": text_output}]}}],
            "usageMetadata": self._get_usage_metadata(response),
        }

    def _generate_text_with_sdk(
        self,
        payload: GatewayExecuteRequest,
        provider_request: dict,
        *,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
    ) -> dict:
        if genai is None:
            raise ProviderExecutionError(
                message="google-generativeai package is required for text generation",
                provider_request=provider_request,
            )

        settings = get_settings()
        resolved_max_retries = settings.provider_max_retries if max_retries is None else max_retries
        max_attempts = max(1, resolved_max_retries + 1)
        resolved_timeout = settings.provider_timeout_seconds if timeout_seconds is None else timeout_seconds
        resolved_timeout = max(resolved_timeout, self.text_min_timeout_seconds)
        genai.configure(api_key=payload.api_key)
        model = genai.GenerativeModel(payload.model)
        kwargs: dict[str, Any] = {
            "safety_settings": self.text_safety_settings,
            "request_options": {"timeout": resolved_timeout},
        }

        for attempt in range(max_attempts):
            try:
                try:
                    response = model.generate_content(provider_request["contents"], **kwargs)
                except TypeError:
                    if "request_options" not in kwargs:
                        raise
                    kwargs.pop("request_options", None)
                    response = model.generate_content(provider_request["contents"], **kwargs)
                return self._normalize_text_sdk_response(response)
            except Exception as exc:
                status_code = self._extract_exception_status_code(exc)
                should_retry = status_code in self.sdk_retry_status_codes
                if should_retry and attempt < max_attempts - 1:
                    sleep(settings.provider_retry_base_delay_seconds * (2**attempt))
                    continue
                response_data = self._extract_exception_response(exc)
                raise ProviderExecutionError(
                    message=str(exc),
                    provider_request=provider_request,
                    provider_response=response_data,
                    provider_status_code=status_code,
                ) from exc

        raise ProviderExecutionError(message="Google GenAI SDK request failed", provider_request=provider_request)

    @staticmethod
    def _extract_exception_status_code(exc: Exception) -> int | None:
        code = getattr(exc, "code", None)
        if callable(code):
            try:
                code = code()
            except Exception:
                code = None
        if isinstance(code, int):
            return code
        value = getattr(code, "value", None)
        if isinstance(value, int):
            return value
        status_code = getattr(exc, "status_code", None)
        if isinstance(status_code, int):
            return status_code
        response = getattr(exc, "response", None)
        response_status_code = getattr(response, "status_code", None)
        if isinstance(response_status_code, int):
            return response_status_code
        match = re.match(r"^\s*(\d{3})\b", str(exc))
        if match:
            return int(match.group(1))
        return None

    @staticmethod
    def _extract_exception_response(exc: Exception) -> dict | str | None:
        response = getattr(exc, "response", None)
        if response is None:
            return None
        if isinstance(response, (dict, str)):
            return response
        if hasattr(response, "json"):
            try:
                parsed = response.json()
                if isinstance(parsed, (dict, str)):
                    return parsed
            except Exception:
                pass
        text = getattr(response, "text", None)
        return str(text) if text else None

    def _post_provider_request(
        self,
        payload: GatewayExecuteRequest,
        provider_request: dict,
        *,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
    ) -> dict:
        settings = get_settings()
        last_exc = None
        provider_response: dict = {}
        resolved_max_retries = settings.provider_max_retries if max_retries is None else max_retries
        max_attempts = max(1, resolved_max_retries + 1)
        resolved_timeout = settings.provider_timeout_seconds if timeout_seconds is None else timeout_seconds

        for attempt in range(max_attempts):
            try:
                response = httpx.post(
                    f"{self.base_url}/models/{payload.model}:generateContent",
                    headers={
                        "x-goog-api-key": payload.api_key,
                        "Content-Type": "application/json",
                    },
                    json=provider_request,
                    timeout=resolved_timeout,
                )
                response.raise_for_status()
                provider_response = response.json()
                break
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                status_code = exc.response.status_code
                response_text = exc.response.text.strip()
                try:
                    parsed_response = exc.response.json()
                except ValueError:
                    parsed_response = response_text or None

                should_retry = status_code in {429, 503}
                if should_retry and attempt < max_attempts - 1:
                    sleep(settings.provider_retry_base_delay_seconds * (2**attempt))
                    continue

                raise ProviderExecutionError(
                    message=response_text or f"Google GenAI returned status {status_code}",
                    provider_request=provider_request,
                    provider_response=parsed_response,
                    provider_status_code=status_code,
                ) from exc
            except httpx.HTTPError as exc:
                last_exc = exc
                if attempt < max_attempts - 1:
                    sleep(settings.provider_retry_base_delay_seconds * (2**attempt))
                    continue
                raise ProviderExecutionError(
                    message=str(exc),
                    provider_request=provider_request,
                ) from exc
        else:
            raise last_exc  # type: ignore[misc]

        return provider_response

    @staticmethod
    def _extract_parts(provider_response: dict) -> list[dict]:
        parts = (
            provider_response.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [])
        )
        if isinstance(parts, list):
            return [part for part in parts if isinstance(part, dict)]
        return []

    @staticmethod
    def _extract_text(parts: list[dict]) -> str:
        return "\n".join(part.get("text", "") for part in parts if part.get("text")).strip()

    @staticmethod
    def _extract_images(parts: list[dict]) -> list[ImageOutput]:
        images: list[ImageOutput] = []
        for part in parts:
            inline_data = part.get("inline_data") or part.get("inlineData")
            if not isinstance(inline_data, dict):
                continue
            data = inline_data.get("data")
            if not data:
                continue
            mime_type = inline_data.get("mime_type") or inline_data.get("mimeType")
            images.append(ImageOutput(mime_type=mime_type, data_base64=data))
        return images

    def generate_text(
        self,
        payload: GatewayExecuteRequest,
        *,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
    ) -> tuple[dict, dict, str]:
        provider_request = self.build_text_sdk_request(payload)
        provider_response = self._generate_text_with_sdk(
            payload,
            provider_request,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )

        parts = self._extract_parts(provider_response)
        text_output = self._extract_text(parts)

        return provider_request, provider_response, text_output

    def generate_image(
        self,
        payload: GatewayExecuteRequest,
        *,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
    ) -> tuple[dict, dict, str | None, list[ImageOutput]]:
        provider_request = self.build_image_request(payload)
        provider_response = self._post_provider_request(
            payload,
            provider_request,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )
        parts = self._extract_parts(provider_response)
        text_output = self._extract_text(parts) or None
        images = self._extract_images(parts)
        return provider_request, provider_response, text_output, images
