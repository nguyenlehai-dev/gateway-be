"""pool api keys and gateway request linkage"""

import json

from alembic import op
import sqlalchemy as sa


revision = "0004_pool_api_keys"
down_revision = "0003_customer_users_and_gateway_keys"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if "pool_api_keys" not in existing_tables:
        op.create_table(
            "pool_api_keys",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("pool_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("provider_api_key", sa.String(length=255), nullable=False),
            sa.Column("provider_api_key_masked", sa.String(length=255), nullable=False),
            sa.Column("project_number", sa.String(length=100), nullable=False),
            sa.Column("status", sa.String(length=50), server_default="active", nullable=False),
            sa.Column("priority", sa.Integer(), server_default="100", nullable=False),
            sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["pool_id"], ["pools.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_pool_api_keys_id"), "pool_api_keys", ["id"], unique=False)
        op.create_index(op.f("ix_pool_api_keys_pool_id"), "pool_api_keys", ["pool_id"], unique=False)

    gateway_request_columns = {column["name"] for column in inspector.get_columns("gateway_requests")}
    gateway_request_indexes = {index["name"] for index in inspector.get_indexes("gateway_requests")}
    dialect_name = conn.dialect.name
    if "selected_pool_api_key_id" not in gateway_request_columns:
        if dialect_name == "sqlite":
            op.add_column("gateway_requests", sa.Column("selected_pool_api_key_id", sa.Integer(), nullable=True))
            op.create_index(op.f("ix_gateway_requests_selected_pool_api_key_id"), "gateway_requests", ["selected_pool_api_key_id"], unique=False)
        else:
            conn.execute(sa.text("DROP TABLE IF EXISTS _alembic_tmp_gateway_requests"))
            with op.batch_alter_table("gateway_requests", recreate="auto") as batch_op:
                batch_op.add_column(sa.Column("selected_pool_api_key_id", sa.Integer(), nullable=True))
                batch_op.create_index(batch_op.f("ix_gateway_requests_selected_pool_api_key_id"), ["selected_pool_api_key_id"], unique=False)
                batch_op.create_foreign_key(
                    "fk_gateway_requests_selected_pool_api_key_id",
                    "pool_api_keys",
                    ["selected_pool_api_key_id"],
                    ["id"],
                    ondelete="SET NULL",
                )
    elif "ix_gateway_requests_selected_pool_api_key_id" not in gateway_request_indexes:
        with op.batch_alter_table("gateway_requests", recreate="auto") as batch_op:
            batch_op.create_index(batch_op.f("ix_gateway_requests_selected_pool_api_key_id"), ["selected_pool_api_key_id"], unique=False)

    pools = conn.execute(sa.text("SELECT id, name, config_json FROM pools")).mappings().all()
    for pool in pools:
        config = pool["config_json"] or {}
        if isinstance(config, str):
            config = json.loads(config)
        provider_api_key = config.get("provider_api_key")
        project_number = config.get("provider_project_number")
        if not provider_api_key or not project_number:
            continue
        existing = conn.execute(
            sa.text("SELECT id FROM pool_api_keys WHERE pool_id = :pool_id LIMIT 1"),
            {"pool_id": pool["id"]},
        ).fetchone()
        if existing is not None:
            continue
        masked = f"{provider_api_key[:4]}{'*' * max(len(provider_api_key) - 6, 0)}{provider_api_key[-2:]}" if len(provider_api_key) > 6 else "*" * len(provider_api_key)
        conn.execute(
            sa.text(
                """
                INSERT INTO pool_api_keys (
                    pool_id, name, provider_api_key, provider_api_key_masked, project_number, status, priority, created_at, updated_at
                ) VALUES (
                    :pool_id, :name, :provider_api_key, :provider_api_key_masked, :project_number, 'active', 100, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
                """
            ),
            {
                "pool_id": pool["id"],
                "name": f"{pool['name']} Primary Key",
                "provider_api_key": provider_api_key,
                "provider_api_key_masked": masked,
                "project_number": project_number,
            },
        )


def downgrade() -> None:
    with op.batch_alter_table("gateway_requests", recreate="auto") as batch_op:
        batch_op.drop_constraint("fk_gateway_requests_selected_pool_api_key_id", type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_gateway_requests_selected_pool_api_key_id"))
        batch_op.drop_column("selected_pool_api_key_id")

    op.drop_index(op.f("ix_pool_api_keys_pool_id"), table_name="pool_api_keys")
    op.drop_index(op.f("ix_pool_api_keys_id"), table_name="pool_api_keys")
    op.drop_table("pool_api_keys")
