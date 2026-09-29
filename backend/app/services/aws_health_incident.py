from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.aws_account import AWSAccount
from app.models.infrastructure_incident import InfrastructureIncident


def record_health_incident(
    db: Session,
    account: AWSAccount,
    *,
    error: str | None,
) -> InfrastructureIncident | None:
    if account.last_health_status != "unhealthy":
        return None

    existing = db.scalar(
        select(InfrastructureIncident)
        .where(
            InfrastructureIncident.organization_id == account.organization_id,
            InfrastructureIncident.aws_account_id == account.id,
            InfrastructureIncident.status == "open",
            InfrastructureIncident.title == "AWS connection unhealthy",
        )
        .order_by(InfrastructureIncident.created_at.desc())
    )
    if existing:
        existing.summary = error or "AWS connection health check failed."
        existing.evidence = [{
            "type": "aws_connection",
            "account_id": account.account_id,
            "credential_mode": account.credential_mode,
            "checked_at": account.last_health_check_at.isoformat() if account.last_health_check_at else None,
            "error": error,
        }]
        return existing

    incident = InfrastructureIncident(
        organization_id=account.organization_id,
        aws_account_id=account.id,
        title="AWS connection unhealthy",
        severity="high",
        status="open",
        started_at=account.last_health_check_at or datetime.now(timezone.utc),
        summary=error or "AWS connection health check failed.",
        evidence=[{
            "type": "aws_connection",
            "account_id": account.account_id,
            "credential_mode": account.credential_mode,
            "checked_at": account.last_health_check_at.isoformat() if account.last_health_check_at else None,
            "error": error,
        }],
    )
    db.add(incident)
    return incident
