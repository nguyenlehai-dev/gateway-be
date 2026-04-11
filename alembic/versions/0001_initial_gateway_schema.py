"""initial gateway schema"""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial_gateway_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vendors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_vendors_id"), "vendors", ["id"], unique=False)
    op.create_index(op.f("ix_vendors_slug"), "vendors", ["slug"], unique=True)
    op.create_index(op.f("ix_vendors_code"), "vendors", ["code"], unique=True)

    op.create_table(
        "pools",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("vendor_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), server_default="active", nullable=False),
        sa.Column("config_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_pools_id"), "pools", ["id"], unique=False)
    op.create_index(op.f("ix_pools_vendor_id"), "pools", ["vendor_id"], unique=False)
    op.create_index(op.f("ix_pools_slug"), "pools", ["slug"], unique=True)
    op.create_index(op.f("ix_pools_code"), "pools", ["code"], unique=False)

    op.create_table(
        "api_functions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pool_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("http_method", sa.String(length=20), server_default="POST", nullable=False),
        sa.Column("path", sa.String(length=255), nullable=True),
        sa.Column("provider_action", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="active", nullable=False),
        sa.Column("schema_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["pool_id"], ["pools.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_api_functions_id"), "api_functions", ["id"], unique=False)
    op.create_index(op.f("ix_api_functions_pool_id"), "api_functions", ["pool_id"], unique=False)
    op.create_index(op.f("ix_api_functions_code"), "api_functions", ["code"], unique=False)

    op.create_table(
        "gateway_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("vendor_id", sa.Integer(), nullable=False),
        sa.Column("pool_id", sa.Integer(), nullable=False),
        sa.Column("api_function_id", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.String(length=100), nullable=False),
        sa.Column("model", sa.String(length=255), nullable=False),
        sa.Column("project_number", sa.String(length=100), nullable=False),
        sa.Column("api_key_masked", sa.String(length=255), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("provider_request_json", sa.JSON(), nullable=True),
        sa.Column("provider_response_json", sa.JSON(), nullable=True),
        sa.Column("output_text", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), server_default="pending", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["api_function_id"], ["api_functions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["pool_id"], ["pools.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_gateway_requests_id"), "gateway_requests", ["id"], unique=False)
    op.create_index(op.f("ix_gateway_requests_vendor_id"), "gateway_requests", ["vendor_id"], unique=False)
    op.create_index(op.f("ix_gateway_requests_pool_id"), "gateway_requests", ["pool_id"], unique=False)
    op.create_index(op.f("ix_gateway_requests_api_function_id"), "gateway_requests", ["api_function_id"], unique=False)
    op.create_index(op.f("ix_gateway_requests_request_id"), "gateway_requests", ["request_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_gateway_requests_request_id"), table_name="gateway_requests")
    op.drop_index(op.f("ix_gateway_requests_api_function_id"), table_name="gateway_requests")
    op.drop_index(op.f("ix_gateway_requests_pool_id"), table_name="gateway_requests")
    op.drop_index(op.f("ix_gateway_requests_vendor_id"), table_name="gateway_requests")
    op.drop_index(op.f("ix_gateway_requests_id"), table_name="gateway_requests")
    op.drop_table("gateway_requests")

    op.drop_index(op.f("ix_api_functions_code"), table_name="api_functions")
    op.drop_index(op.f("ix_api_functions_pool_id"), table_name="api_functions")
    op.drop_index(op.f("ix_api_functions_id"), table_name="api_functions")
    op.drop_table("api_functions")

    op.drop_index(op.f("ix_pools_code"), table_name="pools")
    op.drop_index(op.f("ix_pools_slug"), table_name="pools")
    op.drop_index(op.f("ix_pools_vendor_id"), table_name="pools")
    op.drop_index(op.f("ix_pools_id"), table_name="pools")
    op.drop_table("pools")

    op.drop_index(op.f("ix_vendors_code"), table_name="vendors")
    op.drop_index(op.f("ix_vendors_slug"), table_name="vendors")
    op.drop_index(op.f("ix_vendors_id"), table_name="vendors")
    op.drop_table("vendors")
