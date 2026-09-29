from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.db import Base


class InfrastructureEvent(Base):
    __tablename__ = "infrastructure_events"
    __table_args__ = (UniqueConstraint("aws_account_id", "event_id", name="uq_aws_account_event"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    aws_account_id: Mapped[int] = mapped_column(ForeignKey("aws_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    event_id: Mapped[str] = mapped_column(String(256), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False, default="aws.cloudtrail")
    event_name: Mapped[str] = mapped_column(String(200), nullable=False)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    region: Mapped[str | None] = mapped_column(String(32))
    resource_type: Mapped[str | None] = mapped_column(String(200))
    resource_id: Mapped[str | None] = mapped_column(String(500))
    actor: Mapped[str | None] = mapped_column(String(500))
    raw_event: Mapped[dict] = mapped_column(JSON, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)

    aws_account = relationship("AWSAccount", back_populates="events")
