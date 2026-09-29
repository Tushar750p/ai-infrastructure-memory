from datetime import datetime

from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.aws_account import AWSAccount
from app.models.infrastructure_event import InfrastructureEvent
from app.services.aws_credentials import build_aws_session, decrypt_secret


def _resource_details(event: dict) -> tuple[str | None, str | None]:
    resources = event.get("Resources") or []
    if resources:
        first = resources[0]
        return first.get("ResourceType"), first.get("ResourceName")
    return None, None


def _actor(event: dict) -> str | None:
    identity = event.get("Username") or event.get("Resources", [{}])[0].get("Username") if event.get("Resources") else event.get("Username")
    if identity:
        return str(identity)
    return None


def _normalize(event: dict, account: AWSAccount) -> InfrastructureEvent:
    resource_type, resource_id = _resource_details(event)
    event_time = event.get("EventTime")
    if not isinstance(event_time, datetime):
        raise ValueError("CloudTrail event is missing EventTime")

    event_name = event.get("EventName") or "UnknownEvent"
    service = event.get("EventSource") or "aws.cloudtrail"
    actor = _actor(event)
    summary = f"{event_name} by {actor or 'unknown actor'}"

    return InfrastructureEvent(
        organization_id=account.organization_id,
        aws_account_id=account.id,
        event_id=event["EventId"],
        source=service,
        event_name=event_name,
        event_time=event_time,
        region=event.get("AwsRegion") or account.region,
        resource_type=resource_type,
        resource_id=resource_id,
        actor=actor,
        raw_event=event,
        summary=summary,
    )


def collect_cloudtrail_events(
    db: Session,
    account: AWSAccount,
    encryption_key: str,
    start_time: datetime,
    end_time: datetime,
) -> int:
    access_key_id = decrypt_secret(account.encrypted_access_key_id, encryption_key)
    secret_access_key = decrypt_secret(account.encrypted_secret_access_key, encryption_key)
    session = build_aws_session(access_key_id, secret_access_key, account.region)
    client = session.client("cloudtrail", region_name=account.region)

    inserted = 0
    paginator = client.get_paginator("lookup_events")
    try:
        pages = paginator.paginate(
            StartTime=start_time,
            EndTime=end_time,
            PaginationConfig={"PageSize": 50},
        )
        for page in pages:
            for event in page.get("Events", []):
                event_id = event.get("EventId")
                if not event_id:
                    continue
                exists = db.scalar(
                    select(InfrastructureEvent.id).where(
                        InfrastructureEvent.aws_account_id == account.id,
                        InfrastructureEvent.event_id == event_id,
                    )
                )
                if exists:
                    continue
                db.add(_normalize(event, account))
                inserted += 1
        db.commit()
    except (BotoCoreError, ClientError):
        db.rollback()
        raise

    return inserted
