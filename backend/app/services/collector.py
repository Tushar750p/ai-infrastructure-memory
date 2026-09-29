import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.config import get_settings
from app.database.db import SessionLocal
from app.models.aws_account import AWSAccount
from app.services.cloudtrail import collect_cloudtrail_events

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
