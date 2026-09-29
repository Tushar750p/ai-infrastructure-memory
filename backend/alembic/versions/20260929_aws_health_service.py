"""record aws health service fields

Revision ID: 20260929_health_service
Revises: 20260929_aws_health
Create Date: 2026-09-29
"""
# This revision intentionally contains no schema changes.
# The health columns were introduced by 20260929_aws_health.
from alembic import op

revision = "20260929_health_service"
down_revision = "20260929_aws_health"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
