import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.config import get_settings
from app.database.db import SessionLocal
from app.models.aws_account import AWSAccount
from app.models.infrastructure_incident import InfrastructureIncident
from app.services.aws_inventory import sync_aws_inventory
from app.services.aws_health import update_account_health
from app.services.aws_health_incident import record_health_incident
from app.services.cloudtrail import collect_cloudtrail_events
from app.services.incident_detection import detect_incidents_for_account
from app.services.cloudwatch import collect_cloudwatch_metrics

logger = logging.getLogger(__name__)


def sync_all_accounts() -> int:
    settings = get_settings()
    db = SessionLocal()
    total = 0
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(minutes=15)
    try:
        accounts = db.scalars(
            select(AWSAccount).where(AWSAccount.enabled.is_(True))
        ).all()
        for account in accounts:
            try:
                health = update_account_health(account, settings.credentials_encryption_key, settings.aws_session_duration_seconds)
                record_health_incident(db, account, error=account.last_health_error)
                if health == "healthy":
                    open_incident = db.scalar(select(InfrastructureIncident).where(
                        InfrastructureIncident.organization_id == account.organization_id,
                        InfrastructureIncident.aws_account_id == account.id,
                        InfrastructureIncident.status == "open",
                        InfrastructureIncident.title == "AWS connection unhealthy",
                    ))
                    if open_incident:
                        open_incident.status = "resolved"
                        open_incident.resolved_at = account.last_health_check_at
                        open_incident.root_cause = "AWS connection health check recovered."
                db.commit()
                logger.info("AIME AWS health for account %s: %s", account.id, health)
            except Exception:
                db.rollback()
                logger.exception("AWS health check failed for account %s", account.id)

            try:
                total += collect_cloudtrail_events(
                    db,
                    account,
                    settings.credentials_encryption_key,
                    start_time,
                    end_time,
                )
            except Exception:
                logger.exception("CloudTrail collection failed for account %s", account.id)

            try:
                metrics = collect_cloudwatch_metrics(
                    db,
                    account,
                    settings.credentials_encryption_key,
                    lookback_minutes=15,
                )
                if metrics:
                    logger.info(
                        "AIME stored %s CloudWatch datapoints for account %s",
                        metrics,
                        account.id,
                    )
            except Exception:
                logger.exception("CloudWatch collection failed for account %s", account.id)

            try:
                detected = detect_incidents_for_account(
                    db,
                    organization_id=account.organization_id,
                    aws_account_id=account.id,
                    lookback_minutes=15,
                )
                if detected:
                    logger.info(
                        "AIME detected %s candidate incident(s) for account %s",
                        detected,
                        account.id,
                    )
            except Exception:
                logger.exception("Incident detection failed for account %s", account.id)

            try:
                discovered = sync_aws_inventory(
                    db,
                    account,
                    settings.credentials_encryption_key,
                )
                if discovered:
                    logger.info(
                        "AIME inventory discovered %s resources for account %s",
                        discovered,
                        account.id,
                    )
            except Exception:
                logger.exception("AWS inventory collection failed for account %s", account.id)
        return total
    finally:
        db.close()


async def cloudtrail_worker(stop_event: asyncio.Event) -> None:
    interval = 300
    while not stop_event.is_set():
        try:
            inserted = await asyncio.to_thread(sync_all_accounts)
            if inserted:
                logger.info("AIME collector stored %s new infrastructure events", inserted)
        except Exception:
            logger.exception("AIME CloudTrail collector failed")

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except asyncio.TimeoutError:
            pass
