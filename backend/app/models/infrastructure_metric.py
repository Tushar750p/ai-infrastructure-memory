from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.db import Base


class InfrastructureMetric(Base):
    __tablename__ = "infrastructure_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    aws_account_id: Mapped[int] = mapped_column(
        ForeignKey("aws_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    resource_id: Mapped[int | None] = mapped_column(
        ForeignKey("infrastructure_resources.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    namespace: Mapped[str] = mapped_column(String(100), nullable=False, default="AWS/EC2")
    metric_name: Mapped[str] = mapped_column(String(200), nullable=False)
    dimensions: Mapped[dict | None] = mapped_column(JSON)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    value: Mapped[float] = mapped_column(nullable=False)
    unit: Mapped[str | None] = mapped_column(String(50))
    statistic: Mapped[str] = mapped_column(String(50), nullable=False, default="Average")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
