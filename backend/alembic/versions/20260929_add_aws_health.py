"""add aws connection health fields

Revision ID: 20260929_aws_health
Revises: 20260929_aws_role
Create Date: 2026-09-29
"""
from alembic import op
import sqlalchemy as sa

revision = "20260929_aws_health"
down_revision = "20260929_aws_role"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("aws_accounts", sa.Column("last_health_check_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("aws_accounts", sa.Column("last_health_status", sa.String(length=32), nullable=True))
    op.add_column("aws_accounts", sa.Column("last_health_error", sa.String(length=1000), nullable=True))


def downgrade() -> None:
    op.drop_column("aws_accounts", "last_health_error")
    op.drop_column("aws_accounts", "last_health_status")
    op.drop_column("aws_accounts", "last_health_check_at")
