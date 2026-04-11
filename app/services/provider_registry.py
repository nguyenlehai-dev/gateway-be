from fastapi import HTTPException, status

from app.services.google_genai_service import GoogleGenAIService


class ProviderRegistry:
    """Maps vendor/provider actions to executable services."""

    def resolve(self, vendor_code: str, provider_action: str):
        if vendor_code == "google" and provider_action in {
            "google.genai.text_generation",
            "google.genai.image_generation",
        }:
            return GoogleGenAIService()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No provider registered for vendor={vendor_code}, action={provider_action}",
        )
