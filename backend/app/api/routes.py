from datetime import datetime, timedelta, timezone

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.db import get_db
from app.models.aws_account import AWSAccount
from app.models.infrastructure_event import InfrastructureEvent
from app.models.organization import Organization
from app.services.aws_credentials import build_aws_session, encrypt_secret
from app.services.cloudtrail import collect_cloudtrail_events

router = APIRouter(prefix="/api", tags=["infrastructure"])


class AWSAccountCreate(BaseModel):
    organization_name: str = Field(min_length=1, max_length=200)
    access_key_id: str = Field(min_length=16, max_length=128)
    secret_access_key: str = Field(min_length=16, max_length=256)
    region: str = Field(default="us-east-1", min_length=1, max_length=32)


@router.post("/aws/accounts")
def add_aws_account(payload: AWSAccountCreate, db: Session = Depends(get_db)):
    settings = get_settings()
    session = build_aws_session(payload.access_key_id, payload.secret_access_key, payload.region)
    try:
        identity = session.client("sts", region_name=payload.region).get_caller_identity()
    except (BotoCoreError, ClientError) as exc:
        raise HTTPException(status_code=400, detail="AWS credential verification failed") from exc

    account_id = identity.get("Account")
    if not account_id:
        raise HTTPException(status_code=400, detail="AWS account ID could not be determined")

    organization = db.scalar(select(Organization).where(Organization.name == payload.organization_name))
    if not organization:
        organization = Organization(name=payload.organization_name)
        db.add(organization)
        db.flush()

    existing = db.scalar(
        select(AWSAccount).where(
            AWSAccount.organization_id == organization.id,
            AWSAccount.account_id == account_id,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="AWS account is already connected")

    account = AWSAccount(
        organization_id=organization.id,
        account_id=account_id,
        region=payload.region,
        encrypted_access_key_id=encrypt_secret(payload.access_key_id, settings.credentials_encryption_key),
        encrypted_secret_access_key=encrypt_secret(payload.secret_access_key, settings.credentials_encryption_key),
        enabled=True,
    )
    db.add(account)
    db.commit()
    db.refresh(account)

    return {
        "account_id": account.id,
        "aws_account_id": account.account_id,
        "organization_id": account.organization_id,
        "region": account.region,
        "status": "connected",
    }


@router.get("/organizations/{organization_id}/events")
def list_infrastructure_events(
    organization_id: int,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    limit = max(1, min(limit, 200))
    events = db.scalars(
        select(InfrastructureEvent)
        .where(InfrastructureEvent.organization_id == organization_id)
        .order_by(InfrastructureEvent.event_time.desc())
        .limit(limit)
    ).all()
    return {
        "organization_id": organization_id,
        "count": len(events),
        "events": [
            {
                "id": event.id,
                "aws_account_id": event.aws_account_id,
                "event_id": event.event_id,
                "source": event.source,
                "event_name": event.event_name,
                "event_time": event.event_time,
                "region": event.region,
                "resource_type": event.resource_type,
                "resource_id": event.resource_id,
                "actor": event.actor,
                "summary": event.summary,
            }
            for event in events
        ],
    }


@router.post("/aws/accounts/{account_id}/cloudtrail/sync")
def sync_cloudtrail(account_id: int, db: Session = Depends(get_db)):
    account = db.scalar(select(AWSAccount).where(AWSAccount.id == account_id, AWSAccount.enabled.is_(True)))
    if not account:
        raise HTTPException(status_code=404, detail="AWS account not found")

    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(minutes=15)
    try:
        inserted = collect_cloudtrail_events(
            db, account, get_settings().credentials_encryption_key, start_time, end_time
        )
    except (BotoCoreError, ClientError) as exc:
        raise HTTPException(status_code=502, detail="CloudTrail synchronization failed") from exc

    return {
        "account_id": account.id,
        "organization_id": account.organization_id,
        "source": "aws.cloudtrail",
        "window_minutes": 15,
        "events_inserted": inserted,
    }
