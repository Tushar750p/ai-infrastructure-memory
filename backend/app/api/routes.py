from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.db import get_db
from app.models.aws_account import AWSAccount
from app.services.cloudtrail import collect_cloudtrail_events

router = APIRouter(prefix="/api", tags=["infrastructure"])


@router.post("/aws/accounts/{account_id}/cloudtrail/sync")
def sync_cloudtrail(account_id: int, db: Session = Depends(get_db)):
    account = db.scalar(select(AWSAccount).where(AWSAccount.id == account_id, AWSAccount.enabled.is_(True)))
    if not account:
        raise HTTPException(status_code=404, detail="AWS account not found")

    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(minutes=15)
    inserted = collect_cloudtrail_events(db, account, get_settings().credentials_encryption_key, start_time, end_time)

    return {"account_id": account.id, "organization_id": account.organization_id, "source": "aws.cloudtrail", "window_minutes": 15, "events_inserted": inserted}
