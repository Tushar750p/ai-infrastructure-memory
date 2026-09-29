from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import get_settings
from app.database.db import Base
from app.models.aws_account import AWSAccount  # noqa: F401
from app.models.infrastructure_event import InfrastructureEvent  # noqa: F401
from app.models.infrastructure_incident import InfrastructureIncident  # noqa: F401
from app.models.infrastructure_fix import InfrastructureFix  # noqa: F401
from app.models.infrastructure_metric import InfrastructureMetric  # noqa: F401
from app.models.incident_knowledge_edge import IncidentKnowledgeEdge  # noqa: F401
from app.models.infrastructure_graph import InfrastructureRelationship, InfrastructureResource  # noqa: F401
from app.models.organization import Organization  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.organization_membership import OrganizationMembership  # noqa: F401
from app.models.user_session import UserSession  # noqa: F401
from app.models.password_reset_token import PasswordResetToken
from app.models.auth_audit_log import AuthAuditLog  # noqa: F401

config = context.config
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))

if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
