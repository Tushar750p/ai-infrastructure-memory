from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.db import Base


class InfrastructureResource(Base):
    __tablename__ = "infrastructure_resources"
    __table_args__ = (
        UniqueConstraint(
            "aws_account_id",
            "resource_type",
            "resource_id",
            name="uq_aws_resource",
        ),
    )

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
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(500), nullable=False)
    name: Mapped[str | None] = mapped_column(String(500))
    region: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    relationships_out = relationship(
        "InfrastructureRelationship",
        foreign_keys="InfrastructureRelationship.source_resource_id",
        back_populates="source_resource",
        cascade="all, delete-orphan",
    )
    relationships_in = relationship(
        "InfrastructureRelationship",
        foreign_keys="InfrastructureRelationship.target_resource_id",
        back_populates="target_resource",
        cascade="all, delete-orphan",
    )


class InfrastructureRelationship(Base):
    __tablename__ = "infrastructure_relationships"
    __table_args__ = (
        UniqueConstraint(
            "source_resource_id",
            "target_resource_id",
            "relationship_type",
            name="uq_infra_relationship",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_resource_id: Mapped[int] = mapped_column(
        ForeignKey("infrastructure_resources.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_resource_id: Mapped[int] = mapped_column(
        ForeignKey("infrastructure_resources.id", ondelete="CASCADE"),
        nullable=False,
    )
    relationship_type: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    source_resource = relationship(
        "InfrastructureResource",
        foreign_keys=[source_resource_id],
        back_populates="relationships_out",
    )
    target_resource = relationship(
        "InfrastructureResource",
        foreign_keys=[target_resource_id],
        back_populates="relationships_in",
    )
