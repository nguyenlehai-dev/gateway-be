"""customer users and gateway api keys"""

from alembic import op
import sqlalchemy as sa


revision = "0003_customer_users_and_gateway_keys"
down_revision = "0002_add_users_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users", recreate="auto") as batch_op:
        batch_op.add_column(sa.Column("email", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("pool_id", sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f("ix_users_email"), ["email"], unique=True)
        batch_op.create_index(batch_op.f("ix_users_pool_id"), ["pool_id"], unique=False)
        batch_op.create_foreign_key("fk_users_pool_id_pools", "pools", ["pool_id"], ["id"], ondelete="SET NULL")

    op.create_table(
        "gateway_api_keys",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("pool_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("key_hash", sa.String(length=255), nullable=False),
        sa.Column("key_masked", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="active", nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["pool_id"], ["pools.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_gateway_api_keys_id"), "gateway_api_keys", ["id"], unique=False)
    op.create_index(op.f("ix_gateway_api_keys_pool_id"), "gateway_api_keys", ["pool_id"], unique=False)
    op.create_index(op.f("ix_gateway_api_keys_user_id"), "gateway_api_keys", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_gateway_api_keys_user_id"), table_name="gateway_api_keys")
    op.drop_index(op.f("ix_gateway_api_keys_pool_id"), table_name="gateway_api_keys")
    op.drop_index(op.f("ix_gateway_api_keys_id"), table_name="gateway_api_keys")
    op.drop_table("gateway_api_keys")

    with op.batch_alter_table("users", recreate="auto") as batch_op:
        batch_op.drop_constraint("fk_users_pool_id_pools", type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_users_pool_id"))
        batch_op.drop_index(batch_op.f("ix_users_email"))
        batch_op.drop_column("pool_id")
        batch_op.drop_column("email")
