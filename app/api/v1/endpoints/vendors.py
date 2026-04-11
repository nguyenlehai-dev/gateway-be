from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.core.security import GatewayKeyContext, require_admin, require_operator_or_gateway_key
from app.models.vendor import Vendor
from app.schemas.vendor import VendorCreate, VendorListResponse, VendorRead, VendorUpdate
from app.utils.crud import ensure_unique, get_object_or_404, paginate
from app.utils.validators import validate_status

router = APIRouter()


@router.get(
    "",
    response_model=VendorListResponse,
    summary="List vendors",
    description="Danh sach vendor, ho tro search va filter status.",
)
def list_vendors(
    search: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(db_session),
    access: object = Depends(require_operator_or_gateway_key),
) -> VendorListResponse:
    validate_status(status_filter)
    stmt = select(Vendor).order_by(Vendor.id.desc())
    if isinstance(access, GatewayKeyContext):
        stmt = stmt.where(Vendor.id == access.vendor_id)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(or_(Vendor.name.ilike(pattern), Vendor.slug.ilike(pattern), Vendor.code.ilike(pattern)))
    if status_filter:
        stmt = stmt.where(Vendor.status == status_filter)

    items, total = paginate(stmt, db, offset, limit)
    return VendorListResponse(items=items, total=total)


@router.post("", response_model=VendorRead, status_code=status.HTTP_201_CREATED)
def create_vendor(
    payload: VendorCreate,
    db: Session = Depends(db_session),
    _: object = Depends(require_admin),
) -> VendorRead:
    validate_status(payload.status)
    ensure_unique(db, Vendor, "slug", payload.slug, "Vendor slug already exists")
    ensure_unique(db, Vendor, "code", payload.code, "Vendor code already exists")

    vendor = Vendor(**payload.model_dump())
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return vendor


@router.get(
    "/{vendor_id}",
    response_model=VendorRead,
    summary="Get vendor",
    description="Chi tiet vendor theo id.",
)
def get_vendor(
    vendor_id: int,
    db: Session = Depends(db_session),
    access: object = Depends(require_operator_or_gateway_key),
) -> VendorRead:
    if isinstance(access, GatewayKeyContext) and vendor_id != access.vendor_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")
    return get_object_or_404(db, Vendor, vendor_id, "Vendor")


@router.put("/{vendor_id}", response_model=VendorRead)
@router.patch("/{vendor_id}", response_model=VendorRead)
def update_vendor(
    vendor_id: int,
    payload: VendorUpdate,
    db: Session = Depends(db_session),
    _: object = Depends(require_admin),
) -> VendorRead:
    vendor = get_object_or_404(db, Vendor, vendor_id, "Vendor")
    data = payload.model_dump(exclude_unset=True)
    validate_status(data.get("status"))

    if "slug" in data:
        ensure_unique(db, Vendor, "slug", data["slug"], "Vendor slug already exists", exclude_id=vendor_id)
    if "code" in data:
        ensure_unique(db, Vendor, "code", data["code"], "Vendor code already exists", exclude_id=vendor_id)

    for key, value in data.items():
        setattr(vendor, key, value)

    db.commit()
    db.refresh(vendor)
    return vendor


@router.delete("/{vendor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vendor(vendor_id: int, db: Session = Depends(db_session), _: object = Depends(require_admin)) -> None:
    vendor = get_object_or_404(db, Vendor, vendor_id, "Vendor")
    if vendor.gateway_requests:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Vendor cannot be deleted because it already has gateway requests",
        )
    db.delete(vendor)
    db.commit()
