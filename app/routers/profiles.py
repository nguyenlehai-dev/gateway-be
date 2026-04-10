from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Profile, Proxy
from app.schemas import CookieImportResponse, ProfileCreate, ProfileRead, ProfileUpdate
from app.services.cookies import parse_cookie_payload

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("", response_model=list[ProfileRead])
def list_profiles(db: Session = Depends(get_db)) -> list[Profile]:
    return list(db.scalars(select(Profile).order_by(Profile.created_at.desc())).all())


@router.post("", response_model=ProfileRead, status_code=status.HTTP_201_CREATED)
def create_profile(payload: ProfileCreate, db: Session = Depends(get_db)) -> Profile:
    if payload.proxy_id is not None and db.get(Proxy, payload.proxy_id) is None:
        raise HTTPException(status_code=404, detail="Proxy not found")
    profile = Profile(**payload.model_dump())
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.patch("/{profile_id}", response_model=ProfileRead)
def update_profile(profile_id: int, payload: ProfileUpdate, db: Session = Depends(get_db)) -> Profile:
    profile = db.get(Profile, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(profile, field, value)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.post("/{profile_id}/cookies", response_model=CookieImportResponse)
async def import_cookies(profile_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)) -> CookieImportResponse:
    profile = db.get(Profile, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    payload = await file.read()
    try:
        cookie_format, cookies, raw_cookie = parse_cookie_payload(file.filename or "cookies.txt", payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    profile.cookie_format = cookie_format
    profile.cookies = cookies
    profile.raw_cookie = raw_cookie
    db.add(profile)
    db.commit()
    return CookieImportResponse(profile_id=profile.id, cookie_format=cookie_format, cookie_count=len(cookies))


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(profile_id: int, db: Session = Depends(get_db)) -> None:
    profile = db.get(Profile, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    db.delete(profile)
    db.commit()
