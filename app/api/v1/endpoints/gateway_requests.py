from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.core.security import GatewayKeyContext, require_operator_or_gateway_key
from app.models.gateway_request import GatewayRequest
from app.schemas.gateway_request import GatewayRequestListResponse, GatewayRequestRead
from app.utils.crud import get_object_or_404, paginate

router = APIRouter()


@router.get(
    "",
    response_model=GatewayRequestListResponse,
    summary="List gateway requests",
    description="Lich su request, filter theo vendor/pool/function/status/search/date.",
)
def list_gateway_requests(
    vendor_id: int | None = Query(default=None),
    pool_id: int | None = Query(default=None),
    api_function_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    search: str | None = Query(default=None),
    from_date: datetime | None = Query(default=None),
    to_date: datetime | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(db_session),
    access: object = Depends(require_operator_or_gateway_key),
) -> GatewayRequestListResponse:
    stmt = select(GatewayRequest).order_by(GatewayRequest.id.desc())
    if db.bind is not None and db.bind.dialect.name == "sqlite":
        stmt = stmt.where(func.json_valid(GatewayRequest.payload_json) == 1)
        stmt = stmt.where(
            or_(
                GatewayRequest.provider_request_json.is_(None),
                func.json_valid(GatewayRequest.provider_request_json) == 1,
            )
        )
        stmt = stmt.where(
            or_(
                GatewayRequest.provider_response_json.is_(None),
                func.json_valid(GatewayRequest.provider_response_json) == 1,
            )
        )
    if isinstance(access, GatewayKeyContext):
        stmt = stmt.where(GatewayRequest.pool_id == access.pool_id)
    if vendor_id is not None:
        stmt = stmt.where(GatewayRequest.vendor_id == vendor_id)
    if pool_id is not None:
        stmt = stmt.where(GatewayRequest.pool_id == pool_id)
    if api_function_id is not None:
        stmt = stmt.where(GatewayRequest.api_function_id == api_function_id)
    if status is not None:
        stmt = stmt.where(GatewayRequest.status == status)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                GatewayRequest.request_id.ilike(pattern),
                GatewayRequest.model.ilike(pattern),
                GatewayRequest.project_number.ilike(pattern),
                GatewayRequest.output_text.ilike(pattern),
            )
        )
    if from_date is not None:
        stmt = stmt.where(GatewayRequest.created_at >= from_date)
    if to_date is not None:
        stmt = stmt.where(GatewayRequest.created_at <= to_date)

    items, total = paginate(stmt, db, offset, limit)
    return GatewayRequestListResponse(items=items, total=total)


@router.get(
    "/{request_id}",
    response_model=GatewayRequestRead,
    summary="Get gateway request",
    description="Chi tiet mot request (payload, provider response, output, error).",
)
def get_gateway_request(
    request_id: int,
    db: Session = Depends(db_session),
    access: object = Depends(require_operator_or_gateway_key),
) -> GatewayRequestRead:
    entity = get_object_or_404(db, GatewayRequest, request_id, "Gateway request")
    if isinstance(access, GatewayKeyContext) and entity.pool_id != access.pool_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gateway request not found")
    return entity
