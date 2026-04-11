from fastapi import HTTPException, status

VALID_STATUSES = {"active", "inactive"}
VALID_HTTP_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}


def validate_status(value: str | None) -> None:
    if value is None:
        return
    if value not in VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid status '{value}'. Allowed values: {', '.join(sorted(VALID_STATUSES))}",
        )


def validate_http_method(value: str | None) -> None:
    if value is None:
        return
    if value.upper() not in VALID_HTTP_METHODS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid http_method '{value}'. Allowed values: {', '.join(sorted(VALID_HTTP_METHODS))}",
        )
