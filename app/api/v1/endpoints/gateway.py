from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.core.security import AuthContext, GatewayKeyContext, enforce_rate_limit, get_optional_auth_context, require_operator_or_gateway_key
from app.db.session import SessionLocal
from app.schemas.google_genai import (
    GatewayExecuteRequest,
    GatewayExecuteResponse,
    GatewayJobStatusResponse,
    GatewaySubmitRequest,
    GatewaySubmitResponse,
)
from app.services.gateway_executor import GatewayExecutor

router = APIRouter()


def _process_submitted_request(request_id: str) -> None:
    db = SessionLocal()
    try:
        executor = GatewayExecutor(db)
        executor.process_queued_request(request_id)
    finally:
        db.close()


@router.post(
    "/functions/{function_code}/execute",
    response_model=GatewayExecuteResponse,
    summary="Execute Google GenAI",
    description=(
        "Chay runtime request theo function code. "
        "Ho tro text-generation va image-generation (text-to-image, image-to-image)."
    ),
)
def execute_function(
    function_code: str,
    payload: GatewayExecuteRequest,
    request: Request,
    gateway_api_key_header: str | None = Header(default=None, alias="X-Gateway-Api-Key"),
    db: Session = Depends(db_session),
    auth: AuthContext | None = Depends(get_optional_auth_context),
) -> GatewayExecuteResponse:
    if auth is None and not (payload.gateway_api_key or gateway_api_key_header):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing execute credentials")
    if auth is not None and auth.role not in {"admin", "operator"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Operator role required")

    enforce_rate_limit(request)
    executor = GatewayExecutor(db)
    if gateway_api_key_header and not payload.gateway_api_key:
        payload = payload.model_copy(update={"gateway_api_key": gateway_api_key_header})
    return executor.execute(function_code=function_code, payload=payload)


@router.post(
    "/functions/{function_code}/submit",
    response_model=GatewaySubmitResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit async job",
    description=(
        "Submit job bat dong bo, tra ve request_id de polling hoac webhook. "
        "Worker se xu ly va retry cac loi tam thoi."
    ),
)
def submit_function(
    function_code: str,
    payload: GatewaySubmitRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    gateway_api_key_header: str | None = Header(default=None, alias="X-Gateway-Api-Key"),
    db: Session = Depends(db_session),
    auth: AuthContext | None = Depends(get_optional_auth_context),
) -> GatewaySubmitResponse:
    if auth is None and not (payload.gateway_api_key or gateway_api_key_header):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing submit credentials")
    if auth is not None and auth.role not in {"admin", "operator"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Operator role required")

    enforce_rate_limit(request)
    executor = GatewayExecutor(db)
    if gateway_api_key_header and not payload.gateway_api_key:
        payload = payload.model_copy(update={"gateway_api_key": gateway_api_key_header})

    response = executor.submit(function_code=function_code, payload=payload)
    background_tasks.add_task(_process_submitted_request, response.request_id)
    return response


@router.get(
    "/requests/{request_id}/status",
    response_model=GatewayJobStatusResponse,
    summary="Get job status",
    description="Kiem tra trang thai task async cua end user (queued/retrying/success/failed), ket qua va thong tin retry.",
)
def get_request_status(
    request_id: str,
    db: Session = Depends(db_session),
    access: AuthContext | GatewayKeyContext = Depends(require_operator_or_gateway_key),
) -> GatewayJobStatusResponse:
    executor = GatewayExecutor(db)
    job = executor.get_job_status(request_id)
    if isinstance(access, GatewayKeyContext):
        request_log = executor._get_request_by_request_id(request_id)
        if request_log is None or request_log.pool_id != access.pool_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gateway request not found")
    return job


@router.post(
    "/requests/{request_id}/retry",
    response_model=GatewayJobStatusResponse,
    summary="End-user task recovery",
    description="Endpoint de client/end user khoi phuc mot task da failed tren cung request_id, khong can submit job moi.",
)
def retry_request(
    request_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(db_session),
    access: AuthContext | GatewayKeyContext = Depends(require_operator_or_gateway_key),
) -> GatewayJobStatusResponse:
    executor = GatewayExecutor(db)
    if isinstance(access, GatewayKeyContext):
        request_log = executor._get_request_by_request_id(request_id)
        if request_log is None or request_log.pool_id != access.pool_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gateway request not found")
    response = executor.retry_request(request_id)
    if response.status == "queued":
        background_tasks.add_task(_process_submitted_request, request_id)
    return response
