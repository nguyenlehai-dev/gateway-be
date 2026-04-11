#!/usr/bin/env python3

from pathlib import Path
import sys

from sqlalchemy import select

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.user import User
from app.services.auth_service import hash_password, verify_password


def main() -> None:
    db = SessionLocal()
    try:
        username = settings.bootstrap_admin_username.strip()
        existing = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
        if existing is not None:
            updated = False
            if existing.full_name != settings.bootstrap_admin_full_name:
                existing.full_name = settings.bootstrap_admin_full_name
                updated = True
            if not verify_password(settings.bootstrap_admin_password, existing.password_hash):
                existing.password_hash = hash_password(settings.bootstrap_admin_password)
                updated = True
            if existing.role != "admin":
                existing.role = "admin"
                updated = True
            if existing.status != "active":
                existing.status = "active"
                updated = True
            if updated:
                db.commit()
            print(f"Admin user already exists: {username}")
            return

        user = User(
            username=username,
            full_name=settings.bootstrap_admin_full_name,
            password_hash=hash_password(settings.bootstrap_admin_password),
            role="admin",
            status="active",
        )
        db.add(user)
        db.commit()
        print(f"Created admin user: {username}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
