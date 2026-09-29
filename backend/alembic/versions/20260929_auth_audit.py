"""add auth audit logs

Revision ID: 20260929_auth_audit
Revises: 20260929_password_reset
"""

from alembic import op
import sqlalchemy as sa


revision = "20260929_auth_audit"
down_revision = "20260929_password_reset"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "auth_audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_auth_audit_logs_user_id", "auth_audit_logs", ["user_id"])
    op.create_index("ix_auth_audit_logs_organization_id", "auth_audit_logs", ["organization_id"])
    op.create_index("ix_auth_audit_logs_action", "auth_audit_logs", ["action"])
    op.create_index("ix_auth_audit_logs_created_at", "auth_audit_logs", ["created_at"])


def downgrade():
    op.drop_index("ix_auth_audit_logs_created_at", table_name="auth_audit_logs")
    op.drop_index("ix_auth_audit_logs_action", table_name="auth_audit_logs")
    op.drop_index("ix_auth_audit_logs_organization_id", table_name="auth_audit_logs")
    op.drop_index("ix_auth_audit_logs_user_id", table_name="auth_audit_logs")
    op.drop_table("auth_audit_logs")
