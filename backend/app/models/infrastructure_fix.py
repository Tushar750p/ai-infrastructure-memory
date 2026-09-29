from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.db import Base


class InfrastructureFix(Base):
    __tablename__ = "infrastructure_fixes"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    incident_id: Mapped[int] = mapped_column(
        ForeignKey("infrastructure_incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    resource_id: Mapped[int | None] = mapped_column(
        ForeignKey("infrastructure_resources.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    resolution: Mapped[str] = mapped_column(Text, nullable=False)
    commands: Mapped[list | None] = mapped_column(JSON)
    steps: Mapped[list | None] = mapped_column(JSON)
    outcome: Mapped[str | None] = mapped_column(Text)
    verified: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
