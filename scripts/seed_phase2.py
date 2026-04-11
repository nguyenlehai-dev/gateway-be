#!/usr/bin/env python3

from pathlib import Path
import sys

from sqlalchemy import and_, select

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.db.session import SessionLocal
from app.models.api_function import ApiFunction
from app.models.pool import Pool
from app.models.vendor import Vendor


TEXT_GENERATION_SCHEMA = {
    "type": "object",
    "required": [
        "api_key",
        "project_number",
        "model",
        "prompt",
        "references_image",
        "references_video",
        "references_audios",
    ],
}

IMAGE_GENERATION_SCHEMA = {
    "type": "object",
    "required": [
        "api_key",
        "project_number",
        "model",
        "prompt",
    ],
}


def main() -> None:
    db = SessionLocal()
    try:
        vendor = db.execute(select(Vendor).where(Vendor.code == "google")).scalar_one_or_none()
        if vendor is None:
            vendor = Vendor(
                name="Google",
                slug="google",
                code="google",
                description="Default vendor for Gemini integrations",
                status="active",
            )
            db.add(vendor)
            db.flush()

        pool = db.execute(
            select(Pool).where(and_(Pool.vendor_id == vendor.id, Pool.code == "gemini-api"))
        ).scalar_one_or_none()
        if pool is None:
            pool = Pool(
                vendor_id=vendor.id,
                name="Gemini API",
                slug="gemini-api",
                code="gemini-api",
                description="Google Gemini API pool",
                status="active",
                config_json={"provider": "google", "timeout_seconds": 60},
            )
            db.add(pool)
            db.flush()

        api_function = db.execute(
            select(ApiFunction).where(and_(ApiFunction.pool_id == pool.id, ApiFunction.code == "text-generation"))
        ).scalar_one_or_none()
        if api_function is None:
            api_function = ApiFunction(
                pool_id=pool.id,
                name="Text Generation",
                code="text-generation",
                description="Generate text using Google GenAI",
                http_method="POST",
                path="/api/v1/gateway/functions/text-generation/execute",
                provider_action="google.genai.text_generation",
                status="active",
                schema_json=TEXT_GENERATION_SCHEMA,
            )
            db.add(api_function)

        image_pool = db.execute(
            select(Pool).where(and_(Pool.vendor_id == vendor.id, Pool.code == "image-generation"))
        ).scalar_one_or_none()
        if image_pool is None:
            image_pool = Pool(
                vendor_id=vendor.id,
                name="Image Generation",
                slug="image-generation",
                code="image-generation",
                description="Google Gemini image generation pool",
                status="active",
                config_json={
                    "provider": "google",
                    "timeout_seconds": 60,
                    "default_model": "gemini-3.1-flash-image-preview",
                },
            )
            db.add(image_pool)
            db.flush()

        image_function = db.execute(
            select(ApiFunction).where(
                and_(ApiFunction.pool_id == image_pool.id, ApiFunction.code == "image-generation")
            )
        ).scalar_one_or_none()
        if image_function is None:
            image_function = ApiFunction(
                pool_id=image_pool.id,
                name="Image Generation",
                code="image-generation",
                description="Generate images using Google GenAI",
                http_method="POST",
                path="/api/v1/gateway/functions/image-generation/execute",
                provider_action="google.genai.image_generation",
                status="active",
                schema_json=IMAGE_GENERATION_SCHEMA,
            )
            db.add(image_function)

        db.commit()
        print("Seed completed: Google -> Gemini API -> Text Generation, Image Generation")
    finally:
        db.close()


if __name__ == "__main__":
    main()
