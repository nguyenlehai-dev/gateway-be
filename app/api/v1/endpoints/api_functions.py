from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.core.security import GatewayKeyContext, require_admin, require_operator_or_gateway_key
from app.models.api_function import ApiFunction
from app.models.pool import Pool
from app.schemas.api_function import ApiFunctionCreate, ApiFunctionListResponse, ApiFunctionRead, ApiFunctionUpdate
from app.utils.crud import get_object_or_404, paginate
from app.utils.validators import validate_http_method, validate_status

router = APIRouter()


@router.get(
    "",
    response_model=ApiFunctionListResponse,
    summary="List API functions",
    description="Danh sach API functions theo pool, ho tro search va filter status.",
)
def list_api_functions(
    pool_id: int | None = Query(default=None),
    search: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(db_session),
    access: object = Depends(require_operator_or_gateway_key),
) -> ApiFunctionListResponse:
    validate_status(status_filter)
    stmt = select(ApiFunction).order_by(ApiFunction.id.desc())
    if isinstance(access, GatewayKeyContext):
        stmt = stmt.where(ApiFunction.pool_id == access.pool_id)
    if pool_id is not None:
        stmt = stmt.where(ApiFunction.pool_id == pool_id)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                ApiFunction.name.ilike(pattern),
                ApiFunction.code.ilike(pattern),
                ApiFunction.provider_action.ilike(pattern),
            )
        )
    if status_filter:
        stmt = stmt.where(ApiFunction.status == status_filter)

    items, total = paginate(stmt, db, offset, limit)
    return ApiFunctionListResponse(items=items, total=total)


@router.post("", response_model=ApiFunctionRead, status_code=status.HTTP_201_CREATED)
def create_api_function(
    payload: ApiFunctionCreate,
    db: Session = Depends(db_session),
    _: object = Depends(require_admin),
) -> ApiFunctionRead:
    validate_status(payload.status)
    validate_http_method(payload.http_method)
    get_object_or_404(db, Pool, payload.pool_id, "Pool")
    duplicate = db.execute(
        select(ApiFunction).where(and_(ApiFunction.pool_id == payload.pool_id, ApiFunction.code == payload.code))
    ).scalar_one_or_none()
    if duplicate is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="API Function code already exists in this pool")

    data = payload.model_dump(by_alias=True)
    data["http_method"] = payload.http_method.upper()
    entity = ApiFunction(**data)
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return entity


@router.get(
    "/{api_function_id}",
    response_model=ApiFunctionRead,
    summary="Get API function",
    description="Chi tiet API function theo id.",
)
def get_api_function(
    api_function_id: int,
    db: Session = Depends(db_session),
    access: object = Depends(require_operator_or_gateway_key),
) -> ApiFunctionRead:
    entity = get_object_or_404(db, ApiFunction, api_function_id, "API Function")
    if isinstance(access, GatewayKeyContext) and entity.pool_id != access.pool_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API Function not found")
    return entity


@router.put("/{api_function_id}", response_model=ApiFunctionRead)
@router.patch("/{api_function_id}", response_model=ApiFunctionRead)
def update_api_function(
    api_function_id: int,
    payload: ApiFunctionUpdate,
    db: Session = Depends(db_session),
    _: object = Depends(require_admin),
) -> ApiFunctionRead:
    entity = get_object_or_404(db, ApiFunction, api_function_id, "API Function")
    data = payload.model_dump(exclude_unset=True, by_alias=True)
    validate_status(data.get("status"))
    validate_http_method(data.get("http_method"))

    target_pool_id = data.get("pool_id", entity.pool_id)
    if "pool_id" in data:
        get_object_or_404(db, Pool, target_pool_id, "Pool")
    if "code" in data:
        duplicate = db.execute(
            select(ApiFunction).where(
                and_(ApiFunction.pool_id == target_pool_id, ApiFunction.code == data["code"], ApiFunction.id != api_function_id)
            )
        ).scalar_one_or_none()
        if duplicate is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="API Function code already exists in this pool",
            )

    if "http_method" in data:
        data["http_method"] = data["http_method"].upper()

    for key, value in data.items():
        setattr(entity, key, value)

    db.commit()
    db.refresh(entity)
    return entity


@router.delete("/{api_function_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_api_function(
    api_function_id: int,
    db: Session = Depends(db_session),
    _: object = Depends(require_admin),
) -> None:
    entity = get_object_or_404(db, ApiFunction, api_function_id, "API Function")
    if entity.gateway_requests:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="API Function cannot be deleted because it already has gateway requests",
        )
    db.delete(entity)
    db.commit()
