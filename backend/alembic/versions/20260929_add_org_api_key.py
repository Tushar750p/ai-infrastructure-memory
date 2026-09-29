"""add organization api key

Revision ID: 20260929_org_key
Revises:
Create Date: 2026-09-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20260929_org_key"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = inspector.get_table_names()

    if "organizations" not in tables:
        from app.database.db import Base
        Base.metadata.create_all(bind=bind)
        inspector = inspect(bind)

    columns = {column["name"] for column in inspector.get_columns("organizations")}
    if "api_key_hash" not in columns:
        op.add_column(
            "organizations",
            sa.Column("api_key_hash", sa.String(length=64), nullable=True),
        )
        op.create_index(
            "ix_organizations_api_key_hash",
            "organizations",
            ["api_key_hash"],
            unique=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("organizations")}
    if "api_key_hash" in columns:
        op.drop_index("ix_organizations_api_key_hash", table_name="organizations")
        op.drop_column("organizations", "api_key_hash")
