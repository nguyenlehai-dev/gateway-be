from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db import Base, engine, get_db
from app.models import User
from app.routers import api_keys, auth, jobs, profiles, proxies
from app.routers.auth import get_current_user
from app.routers.system import build_dashboard_stats
from app.utils.security import hash_password

settings = get_settings()


def ensure_default_admin() -> None:
    with Session(engine) as db:
        admin = db.query(User).filter(User.username == settings.admin_username).first()
        if admin:
            return

        admin = User(
            username=settings.admin_username,
            display_name=settings.admin_display_name,
            password_hash=hash_password(settings.admin_password),
            is_active=True,
            last_login_at=datetime.utcnow(),
        )
        db.add(admin)
        db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_default_admin()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

protected_api = [Depends(get_current_user)]
app.include_router(auth.router, prefix="/api")
app.include_router(profiles.router, prefix="/api", dependencies=protected_api)
app.include_router(proxies.router, prefix="/api", dependencies=protected_api)
app.include_router(api_keys.router, prefix="/api", dependencies=protected_api)
app.include_router(jobs.router, prefix="/api", dependencies=protected_api)

frontend_dist = Path(settings.frontend_dist)
assets_dir = frontend_dist / "assets"
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.app_env}


@app.get("/api/dashboard")
def dashboard(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return build_dashboard_stats(db)


@app.get("/{full_path:path}")
def spa_fallback(full_path: str):
    index_file = frontend_dist / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"detail": f"Frontend build not found at {frontend_dist}"}
