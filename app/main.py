from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings

openapi_tags = [
    {"name": "auth", "description": "Dang nhap va lay thong tin user hien tai."},
    {"name": "gateway-keys", "description": "Verify Gateway API key va thong tin pool/cap quyen."},
    {"name": "users", "description": "Quan ly user va phan quyen truy cap."},
    {"name": "vendors", "description": "Quan ly vendor, hien tai co vendor mac dinh la Google."},
    {"name": "pools", "description": "Quan ly pool thuoc vendor, vi du Gemini API."},
    {"name": "pool-api-keys", "description": "Quan ly API key cua provider trong pool."},
    {"name": "api-functions", "description": "Quan ly API function thuoc pool, vi du Text Generation."},
    {"name": "gateway", "description": "Execute Google GenAI (text/image) thong qua function code."},
    {"name": "gateway-requests", "description": "Request history, polling trang thai va thong tin ket qua."},
    {"name": "health", "description": "Healthcheck cho backend service."},
    {"name": "root", "description": "Thong tin root endpoint."},
]

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    version="0.1.0",
    description=(
        "Gateway Backend cung cap CRUD cho Vendor -> Pool -> API Function, "
        "verify Gateway API key, execute Google GenAI (text/image), "
        "doc du lieu (vendors/pools/api-functions), va request history."
    ),
    openapi_url=f"{settings.api_v1_prefix}/openapi.json",
    docs_url=f"{settings.api_v1_prefix}/docs",
    redoc_url=f"{settings.api_v1_prefix}/redoc",
    openapi_tags=openapi_tags,
)

cors_origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/", tags=["root"])
def root() -> dict[str, str]:
    return {"message": "Gateway backend is running"}


@app.get("/up", tags=["health"])
def up() -> dict[str, str]:
    return {"status": "ok", "service": "gateway-be"}
