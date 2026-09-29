"""add aws iam role credential fields

Revision ID: 20260929_aws_role
Revises: 20260929_org_key
Create Date: 2026-09-29
"""
from alembic import op
import sqlalchemy as sa

revision = "20260929_aws_role"
down_revision = "20260929_org_key"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("aws_accounts", sa.Column("credential_mode", sa.String(length=32), nullable=False, server_default="access_key"))
    op.add_column("aws_accounts", sa.Column("role_arn", sa.String(length=2048), nullable=True))
    op.add_column("aws_accounts", sa.Column("external_id", sa.String(length=256), nullable=True))
    op.alter_column("aws_accounts", "encrypted_access_key_id", existing_type=sa.String(length=1024), nullable=True)
    op.alter_column("aws_accounts", "encrypted_secret_access_key", existing_type=sa.String(length=2048), nullable=True)
    op.alter_column("aws_accounts", "credential_mode", server_default=None)


def downgrade() -> None:
    op.alter_column("aws_accounts", "encrypted_secret_access_key", existing_type=sa.String(length=2048), nullable=False)
    op.alter_column("aws_accounts", "encrypted_access_key_id", existing_type=sa.String(length=1024), nullable=False)
    op.drop_column("aws_accounts", "external_id")
    op.drop_column("aws_accounts", "role_arn")
    op.drop_column("aws_accounts", "credential_mode")
