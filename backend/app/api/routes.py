from datetime import datetime, timedelta, timezone

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.db import get_db
from app.models.aws_account import AWSAccount
from app.models.infrastructure_event import InfrastructureEvent
from app.models.infrastructure_graph import InfrastructureRelationship, InfrastructureResource
from app.models.organization import Organization
from app.services.aws_credentials import build_aws_session, encrypt_secret
from app.services.aws_inventory import sync_aws_inventory
from app.services.cloudtrail import collect_cloudtrail_events
from app.services.correlation import correlate_resource_changes
from app.services.incident_analysis import build_root_cause_analysis
from app.models.infrastructure_incident import InfrastructureIncident
from app.models.infrastructure_fix import InfrastructureFix
from app.services.fix_memory import find_similar_fixes

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


@router.get("/organizations/{organization_id}/graph")
def infrastructure_graph(organization_id: int, db: Session = Depends(get_db)):
    resources = db.scalars(
        select(InfrastructureResource)
        .where(InfrastructureResource.organization_id == organization_id)
        .order_by(InfrastructureResource.resource_type, InfrastructureResource.resource_id)
    ).all()
    relationships = db.scalars(
        select(InfrastructureRelationship)
        .where(InfrastructureRelationship.organization_id == organization_id)
    ).all()

    return {
        "organization_id": organization_id,
        "nodes": [
            {
                "id": resource.id,
                "type": resource.resource_type,
                "resource_id": resource.resource_id,
                "name": resource.name,
                "region": resource.region,
                "status": resource.status,
            }
            for resource in resources
        ],
        "edges": [
            {
                "source": relationship.source_resource_id,
                "target": relationship.target_resource_id,
                "type": relationship.relationship_type,
            }
            for relationship in relationships
        ],
    }


class IncidentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    resource_id: int | None = None
    severity: str = Field(default="medium", max_length=50)
    summary: str | None = None


@router.post("/organizations/{organization_id}/incidents")
def create_incident(
    organization_id: int,
    payload: IncidentCreate,
    db: Session = Depends(get_db),
):
    if payload.resource_id is not None:
        resource = db.scalar(
            select(InfrastructureResource).where(
                InfrastructureResource.id == payload.resource_id,
                InfrastructureResource.organization_id == organization_id,
            )
        )
        if not resource:
            raise HTTPException(status_code=404, detail="Infrastructure resource not found")

    incident = InfrastructureIncident(
        organization_id=organization_id,
        resource_id=payload.resource_id,
        title=payload.title,
        severity=payload.severity,
        summary=payload.summary,
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)

    return {
        "id": incident.id,
        "organization_id": incident.organization_id,
        "resource_id": incident.resource_id,
        "title": incident.title,
        "severity": incident.severity,
        "status": incident.status,
        "started_at": incident.started_at,
    }


class FixCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    resolution: str = Field(min_length=1)
    commands: list[str] | None = None
    steps: list[str] | None = None
    outcome: str | None = None
    verified: bool = False
    created_by: str | None = None


@router.post("/organizations/{organization_id}/incidents/{incident_id}/fixes")
def record_incident_fix(
    organization_id: int,
    incident_id: int,
    payload: FixCreate,
    db: Session = Depends(get_db),
):
    incident = db.scalar(
        select(InfrastructureIncident).where(
            InfrastructureIncident.id == incident_id,
            InfrastructureIncident.organization_id == organization_id,
        )
    )
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    fix = InfrastructureFix(
        organization_id=organization_id,
        incident_id=incident.id,
        resource_id=incident.resource_id,
        title=payload.title,
        resolution=payload.resolution,
        commands=payload.commands,
        steps=payload.steps,
        outcome=payload.outcome,
        verified=payload.verified,
        created_by=payload.created_by,
    )
    db.add(fix)

    if payload.verified:
        incident.status = "resolved"
        incident.resolved_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(fix)

    return {
        "id": fix.id,
        "incident_id": fix.incident_id,
        "resource_id": fix.resource_id,
        "title": fix.title,
        "resolution": fix.resolution,
        "commands": fix.commands,
        "steps": fix.steps,
        "outcome": fix.outcome,
        "verified": fix.verified,
        "created_at": fix.created_at,
    }


@router.get("/organizations/{organization_id}/incidents/{incident_id}/similar-fixes")
def similar_incident_fixes(
    organization_id: int,
    incident_id: int,
    limit: int = 5,
    db: Session = Depends(get_db),
):
    incident = db.scalar(
        select(InfrastructureIncident).where(
            InfrastructureIncident.id == incident_id,
            InfrastructureIncident.organization_id == organization_id,
        )
    )
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    fixes = find_similar_fixes(db, incident, limit=limit)
    return {
        "organization_id": organization_id,
        "incident_id": incident_id,
        "count": len(fixes),
        "fixes": fixes,
        "note": "Similarity is evidence-based retrieval. Commands are stored as memory and are not executed automatically.",
    }


@router.get("/organizations/{organization_id}/incidents/{incident_id}/fixes")
def list_incident_fixes(
    organization_id: int,
    incident_id: int,
    db: Session = Depends(get_db),
):
    incident = db.scalar(
        select(InfrastructureIncident).where(
            InfrastructureIncident.id == incident_id,
            InfrastructureIncident.organization_id == organization_id,
        )
    )
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    fixes = db.scalars(
        select(InfrastructureFix)
        .where(
            InfrastructureFix.organization_id == organization_id,
            InfrastructureFix.incident_id == incident_id,
        )
        .order_by(InfrastructureFix.created_at.desc())
    ).all()

    return {
        "incident_id": incident_id,
        "count": len(fixes),
        "fixes": [
            {
                "id": fix.id,
                "title": fix.title,
                "resolution": fix.resolution,
                "commands": fix.commands,
                "steps": fix.steps,
                "outcome": fix.outcome,
                "verified": fix.verified,
                "created_by": fix.created_by,
                "created_at": fix.created_at,
            }
            for fix in fixes
        ],
    }


@router.get("/organizations/{organization_id}/resources/{resource_id}/fix-memory")
def resource_fix_memory(
    organization_id: int,
    resource_id: int,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    resource = db.scalar(
        select(InfrastructureResource).where(
            InfrastructureResource.id == resource_id,
            InfrastructureResource.organization_id == organization_id,
        )
    )
    if not resource:
        raise HTTPException(status_code=404, detail="Infrastructure resource not found")

    fixes = db.scalars(
        select(InfrastructureFix)
        .where(
            InfrastructureFix.organization_id == organization_id,
            InfrastructureFix.resource_id == resource_id,
        )
        .order_by(InfrastructureFix.created_at.desc())
        .limit(max(1, min(limit, 100)))
    ).all()

    return {
        "resource": {
            "id": resource.id,
            "type": resource.resource_type,
            "resource_id": resource.resource_id,
            "name": resource.name,
        },
        "count": len(fixes),
        "fixes": [
            {
                "id": fix.id,
                "incident_id": fix.incident_id,
                "title": fix.title,
                "resolution": fix.resolution,
                "commands": fix.commands,
                "steps": fix.steps,
                "outcome": fix.outcome,
                "verified": fix.verified,
                "created_by": fix.created_by,
                "created_at": fix.created_at,
            }
            for fix in fixes
        ],
    }


@router.get("/organizations/{organization_id}/incidents")
def list_incidents(
    organization_id: int,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    incidents = db.scalars(
        select(InfrastructureIncident)
        .where(InfrastructureIncident.organization_id == organization_id)
        .order_by(InfrastructureIncident.started_at.desc())
        .limit(max(1, min(limit, 200)))
    ).all()
    return {
        "organization_id": organization_id,
        "count": len(incidents),
        "incidents": [
            {
                "id": incident.id,
                "title": incident.title,
                "severity": incident.severity,
                "status": incident.status,
                "resource_id": incident.resource_id,
                "started_at": incident.started_at,
                "resolved_at": incident.resolved_at,
                "summary": incident.summary,
                "root_cause": incident.root_cause,
            }
            for incident in incidents
        ],
    }


@router.get("/organizations/{organization_id}/resources/{resource_id}/rca")
def resource_root_cause_analysis(
    organization_id: int,
    resource_id: int,
    lookback_minutes: int = 60,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    resource = db.scalar(
        select(InfrastructureResource).where(
            InfrastructureResource.id == resource_id,
            InfrastructureResource.organization_id == organization_id,
        )
    )
    if not resource:
        raise HTTPException(status_code=404, detail="Infrastructure resource not found")

    return build_root_cause_analysis(
        db,
        resource,
        lookback_minutes=lookback_minutes,
        limit=limit,
    )


@router.get("/organizations/{organization_id}/resources/{resource_id}/correlation")
def resource_correlation(
    organization_id: int,
    resource_id: int,
    lookback_minutes: int = 60,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    resource = db.scalar(
        select(InfrastructureResource).where(
            InfrastructureResource.id == resource_id,
            InfrastructureResource.organization_id == organization_id,
        )
    )
    if not resource:
        raise HTTPException(status_code=404, detail="Infrastructure resource not found")

    return correlate_resource_changes(
        db,
        resource,
        lookback_minutes=lookback_minutes,
        limit=limit,
    )


@router.post("/aws/accounts/{account_id}/inventory/sync")
def sync_inventory(account_id: int, db: Session = Depends(get_db)):
    account = db.scalar(
        select(AWSAccount).where(
            AWSAccount.id == account_id,
            AWSAccount.enabled.is_(True),
        )
    )
    if not account:
        raise HTTPException(status_code=404, detail="AWS account not found")

    try:
        discovered = sync_aws_inventory(
            db,
            account,
            get_settings().credentials_encryption_key,
        )
    except (BotoCoreError, ClientError) as exc:
        raise HTTPException(status_code=502, detail="AWS inventory synchronization failed") from exc

    return {
        "account_id": account.id,
        "organization_id": account.organization_id,
        "source": "aws.inventory",
        "resources_discovered": discovered,
        "message": "AWS infrastructure inventory synchronized",
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
