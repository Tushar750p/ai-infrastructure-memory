import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.config import get_settings
from app.database.db import SessionLocal
from app.models.aws_account import AWSAccount
from app.services.aws_inventory import sync_aws_inventory
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
