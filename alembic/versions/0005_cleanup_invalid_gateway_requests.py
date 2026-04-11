"""cleanup invalid gateway request json payloads

Revision ID: 0005_cleanup_invalid_gateway_requests
Revises: 0004_pool_api_keys
Create Date: 2026-04-09 12:15:00.000000
"""

from __future__ import annotations

import json

from alembic import op
import sqlalchemy as sa


revision = "0005_cleanup_invalid_gateway_requests"
down_revision = "0004_pool_api_keys"
branch_labels = None
depends_on = None


def _is_valid_json(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, (dict, list)):
        return True
    if isinstance(value, str):
        try:
            json.loads(value)
        except json.JSONDecodeError:
            return False
        return True
    return False


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        bind.execute(
            sa.text(
                """
                DELETE FROM gateway_requests
                WHERE json_valid(payload_json) = 0
                   OR (provider_request_json IS NOT NULL AND json_valid(provider_request_json) = 0)
                   OR (provider_response_json IS NOT NULL AND json_valid(provider_response_json) = 0)
                """
            )
        )
        return

    rows = bind.execute(
        sa.text(
            """
            SELECT id, payload_json, provider_request_json, provider_response_json
            FROM gateway_requests
            """
        )
    ).mappings()

    invalid_ids: list[int] = []
    for row in rows:
        if not _is_valid_json(row["payload_json"]):
            invalid_ids.append(int(row["id"]))
            continue
        if not _is_valid_json(row["provider_request_json"]):
            invalid_ids.append(int(row["id"]))
            continue
        if not _is_valid_json(row["provider_response_json"]):
            invalid_ids.append(int(row["id"]))

    if invalid_ids:
        bind.execute(
            sa.text("DELETE FROM gateway_requests WHERE id IN :ids").bindparams(
                sa.bindparam("ids", expanding=True)
            ),
            {"ids": invalid_ids},
        )


def downgrade() -> None:
    pass
