from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Proxy
from app.schemas import ProxyCreate, ProxyRead

router = APIRouter(prefix="/proxies", tags=["proxies"])


@router.get("", response_model=list[ProxyRead])
def list_proxies(db: Session = Depends(get_db)) -> list[Proxy]:
    return list(db.scalars(select(Proxy).order_by(Proxy.created_at.desc())).all())


@router.post("", response_model=ProxyRead, status_code=status.HTTP_201_CREATED)
def create_proxy(payload: ProxyCreate, db: Session = Depends(get_db)) -> Proxy:
    proxy = Proxy(**payload.model_dump())
    db.add(proxy)
    db.commit()
    db.refresh(proxy)
    return proxy


@router.delete("/{proxy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_proxy(proxy_id: int, db: Session = Depends(get_db)) -> None:
    proxy = db.get(Proxy, proxy_id)
    if proxy is None:
        raise HTTPException(status_code=404, detail="Proxy not found")
    db.delete(proxy)
    db.commit()
