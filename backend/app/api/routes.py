from datetime import datetime, timedelta, timezone

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.db import get_db
from app.models.aws_account import AWSAccount
from app.models.infrastructure_event import InfrastructureEvent
from app.models.infrastructure_graph import InfrastructureRelationship, InfrastructureResource
from app.models.organization import Organization
import hashlib
import secrets
from app.services.aws_credentials import build_aws_session, encrypt_secret, build_role_session, build_account_session
from app.services.aws_health import update_account_health
from app.services.aws_health_incident import record_health_incident
from app.services.aws_inventory import sync_aws_inventory
from app.services.cloudtrail import collect_cloudtrail_events
from app.services.correlation import correlate_resource_changes
from app.services.incident_analysis import build_root_cause_analysis
from app.models.infrastructure_incident import InfrastructureIncident
from app.models.infrastructure_fix import InfrastructureFix
from app.services.fix_memory import find_similar_fixes
from app.services.anomaly_detection import detect_metric_anomalies
from app.services.incident_timeline import build_incident_timeline
from app.services.incident_intelligence import build_incident_intelligence
from app.services.incident_knowledge import build_incident_knowledge_graph

router = APIRouter(prefix="/api", tags=["infrastructure"])

def require_org_access(
    organization_id: int,
    x_aime_api_key: str | None = Header(default=None, alias="X-AIME-API-Key"),
    db: Session = Depends(get_db),
) -> Organization:
    if not x_aime_api_key:
        raise HTTPException(status_code=401, detail="AIME API key required")

    key_hash = hashlib.sha256(x_aime_api_key.encode()).hexdigest()
    organization = db.scalar(
        select(Organization).where(
            Organization.id == organization_id,
            Organization.api_key_hash == key_hash,
        )
    )
    if not organization:
        raise HTTPException(status_code=403, detail="Organization access denied")
    return organization



class AWSAccountCreate(BaseModel):
    api_key: str | None = Field(default=None, min_length=16, max_length=256)
    organization_name: str = Field(min_length=1, max_length=200)
    credential_mode: str = Field(default="access_key", pattern="^(access_key|role)$")
    access_key_id: str | None = Field(default=None, min_length=16, max_length=128)
    secret_access_key: str | None = Field(default=None, min_length=16, max_length=256)
    role_arn: str | None = Field(default=None, max_length=2048)
    external_id: str | None = Field(default=None, max_length=256)
    region: str = Field(default="us-east-1", min_length=1, max_length=32)


@router.post("/aws/accounts")
def add_aws_account(payload: AWSAccountCreate, db: Session = Depends(get_db)):
    settings = get_settings()
    if payload.credential_mode == "role":
        if not payload.role_arn:
            raise HTTPException(status_code=400, detail="role_arn is required for role credential mode")
        try:
            session = build_role_session(payload.role_arn, payload.external_id, payload.region, settings.aws_session_duration_seconds)
        except (BotoCoreError, ClientError) as exc:
            raise HTTPException(status_code=400, detail="AWS IAM role verification failed") from exc
    else:
        if not payload.access_key_id or not payload.secret_access_key:
            raise HTTPException(status_code=400, detail="Access key credentials are required")
        session = build_aws_session(payload.access_key_id, payload.secret_access_key, payload.region)
    try:
        identity = session.client("sts", region_name=payload.region).get_caller_identity()
    except (BotoCoreError, ClientError) as exc:
        raise HTTPException(status_code=400, detail="AWS credential verification failed") from exc

    account_id = identity.get("Account")
    if not account_id:
        raise HTTPException(status_code=400, detail="AWS account ID could not be determined")

    organization = db.scalar(select(Organization).where(Organization.name == payload.organization_name))
    generated_api_key = None
    if not organization:
        generated_api_key = secrets.token_urlsafe(32)
        organization = Organization(
            name=payload.organization_name,
            api_key_hash=hashlib.sha256(generated_api_key.encode()).hexdigest(),
        )
        db.add(organization)
        db.flush()
    elif not payload.api_key or hashlib.sha256(payload.api_key.encode()).hexdigest() != organization.api_key_hash:
        raise HTTPException(status_code=403, detail="Valid organization API key required")

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
        credential_mode=payload.credential_mode,
        role_arn=payload.role_arn,
        external_id=encrypt_secret(payload.external_id, settings.credentials_encryption_key) if payload.external_id else None,
        encrypted_access_key_id=encrypt_secret(payload.access_key_id, settings.credentials_encryption_key) if payload.access_key_id else None,
        encrypted_secret_access_key=encrypt_secret(payload.secret_access_key, settings.credentials_encryption_key) if payload.secret_access_key else None,
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
        **({"api_key": generated_api_key} if generated_api_key else {}),
    }


@router.get("/organizations/{organization_id}/aws/accounts")
def list_aws_accounts(
    organization_id: int,
    db: Session = Depends(get_db),
):
    accounts = db.scalars(
        select(AWSAccount).where(AWSAccount.organization_id == organization_id).order_by(AWSAccount.id)
    ).all()
    return {
        "organization_id": organization_id,
        "accounts": [
            {
                "id": account.id,
                "account_id": account.account_id,
                "region": account.region,
                "credential_mode": account.credential_mode,
                "role_arn": account.role_arn,
                "enabled": account.enabled,
                "last_health_check_at": account.last_health_check_at,
                "last_health_status": account.last_health_status,
                "last_health_error": account.last_health_error,
            }
            for account in accounts
        ],
    }


@router.post("/organizations/{organization_id}/aws/accounts/{account_id}/health", dependencies=[Depends(require_org_access)])
def check_aws_account_health(
    organization_id: int,
    account_id: int,
    db: Session = Depends(get_db),
):
    settings = get_settings()
    account = db.scalar(
        select(AWSAccount).where(
            AWSAccount.id == account_id,
            AWSAccount.organization_id == organization_id,
        )
    )
    if not account:
        raise HTTPException(status_code=404, detail="AWS account not found")

    status = update_account_health(
        account,
        settings.credentials_encryption_key,
        settings.aws_session_duration_seconds,
    )
    record_health_incident(db, account, error=account.last_health_error)
    if status == "healthy":
        open_incident = db.scalar(select(InfrastructureIncident).where(
            InfrastructureIncident.organization_id == organization_id,
            InfrastructureIncident.aws_account_id == account.id,
            InfrastructureIncident.status == "open",
            InfrastructureIncident.title == "AWS connection unhealthy",
        ))
        if open_incident:
            open_incident.status = "resolved"
            open_incident.resolved_at = account.last_health_check_at
            open_incident.root_cause = "AWS connection health check recovered."
    db.commit()

    return {
        "account_id": account.id,
        "aws_account_id": account.account_id,
        "status": status,
        "checked_at": account.last_health_check_at,
        "error": account.last_health_error,
    }


@router.get("/organizations/{organization_id}/events", dependencies=[Depends(require_org_access)])
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


@router.get("/organizations/{organization_id}/graph", dependencies=[Depends(require_org_access)])
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


@router.post("/organizations/{organization_id}/incidents", dependencies=[Depends(require_org_access)])
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


@router.post("/organizations/{organization_id}/incidents/{incident_id}/fixes", dependencies=[Depends(require_org_access)])
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


@router.get("/organizations/{organization_id}/incidents/{incident_id}/knowledge-graph", dependencies=[Depends(require_org_access)])
def incident_knowledge_graph(
    organization_id: int,
    incident_id: int,
    lookback_minutes: int = 120,
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

    return build_incident_knowledge_graph(
        db,
        incident,
        lookback_minutes=lookback_minutes,
    )


@router.get("/organizations/{organization_id}/incidents/{incident_id}/intelligence", dependencies=[Depends(require_org_access)])
def incident_intelligence(
    organization_id: int,
    incident_id: int,
    lookback_minutes: int = 120,
    limit: int = 100,
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

    timeline = build_incident_timeline(
        db,
        incident,
        lookback_minutes=lookback_minutes,
        limit=limit,
    )
    intelligence = build_incident_intelligence(timeline)
    return {
        "incident": timeline["incident"],
        "intelligence": intelligence,
    }


@router.get("/organizations/{organization_id}/incidents/{incident_id}/timeline", dependencies=[Depends(require_org_access)])
def incident_timeline(
    organization_id: int,
    incident_id: int,
    lookback_minutes: int = 120,
    limit: int = 100,
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

    return build_incident_timeline(
        db,
        incident,
        lookback_minutes=lookback_minutes,
        limit=limit,
    )


@router.get("/organizations/{organization_id}/incidents/{incident_id}/similar-fixes", dependencies=[Depends(require_org_access)])
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


@router.get("/organizations/{organization_id}/incidents/{incident_id}/fixes", dependencies=[Depends(require_org_access)])
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


@router.get("/organizations/{organization_id}/resources/{resource_id}/timeline", dependencies=[Depends(require_org_access)])
def resource_incident_timeline(
    organization_id: int,
    resource_id: int,
    lookback_minutes: int = 120,
    limit: int = 100,
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

    incident = db.scalar(
        select(InfrastructureIncident)
        .where(
            InfrastructureIncident.organization_id == organization_id,
            InfrastructureIncident.resource_id == resource_id,
        )
        .order_by(InfrastructureIncident.started_at.desc())
    )
    if not incident:
        return {
            "resource_id": resource_id,
            "incident": None,
            "count": 0,
            "timeline": [],
            "analysis": "No incident history exists for this resource yet.",
        }

    return build_incident_timeline(
        db,
        incident,
        lookback_minutes=lookback_minutes,
        limit=limit,
    )


@router.get("/organizations/{organization_id}/resources/{resource_id}/similar-fixes", dependencies=[Depends(require_org_access)])
def similar_resource_fixes(
    organization_id: int,
    resource_id: int,
    limit: int = 5,
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

    incident = db.scalar(
        select(InfrastructureIncident)
        .where(
            InfrastructureIncident.organization_id == organization_id,
            InfrastructureIncident.resource_id == resource_id,
        )
        .order_by(InfrastructureIncident.started_at.desc())
    )
    if not incident:
        return {
            "resource_id": resource_id,
            "count": 0,
            "fixes": [],
            "note": "No incident history exists for this resource yet.",
        }

    fixes = find_similar_fixes(db, incident, limit=limit)
    return {
        "resource_id": resource_id,
        "incident_id": incident.id,
        "count": len(fixes),
        "fixes": fixes,
    }


@router.get("/organizations/{organization_id}/resources/{resource_id}/fix-memory", dependencies=[Depends(require_org_access)])
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


@router.post("/organizations/{organization_id}/incidents/detect", dependencies=[Depends(require_org_access)])
def detect_incidents(
    organization_id: int,
    lookback_minutes: int = 15,
    db: Session = Depends(get_db),
):
    accounts = db.scalars(
        select(AWSAccount).where(
            AWSAccount.organization_id == organization_id,
            AWSAccount.enabled.is_(True),
        )
    ).all()

    from app.services.incident_detection import detect_incidents_for_account

    detected = 0
    for account in accounts:
        detected += detect_incidents_for_account(
            db,
            organization_id=organization_id,
            aws_account_id=account.id,
            lookback_minutes=lookback_minutes,
        )

    return {
        "organization_id": organization_id,
        "accounts_checked": len(accounts),
        "incidents_created": detected,
        "window_minutes": max(1, min(lookback_minutes, 120)),
        "message": "Candidate incidents detected from high-signal infrastructure changes",
    }


@router.get("/organizations/{organization_id}/incidents", dependencies=[Depends(require_org_access)])
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


@router.get("/organizations/{organization_id}/resources/{resource_id}/rca", dependencies=[Depends(require_org_access)])
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


@router.get("/organizations/{organization_id}/resources/{resource_id}/correlation", dependencies=[Depends(require_org_access)])
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


@router.get("/organizations/{organization_id}/resources/{resource_id}/anomalies", dependencies=[Depends(require_org_access)])
def resource_metric_anomalies(
    organization_id: int,
    resource_id: int,
    lookback_minutes: int = 60,
    baseline_minutes: int = 360,
    z_threshold: float = 2.5,
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

    anomalies = detect_metric_anomalies(
        db,
        organization_id=organization_id,
        resource_id=resource_id,
        lookback_minutes=lookback_minutes,
        baseline_minutes=baseline_minutes,
        z_threshold=max(1.0, min(z_threshold, 10.0)),
        limit=limit,
    )
    return {
        "resource_id": resource_id,
        "lookback_minutes": lookback_minutes,
        "baseline_minutes": baseline_minutes,
        "z_threshold": z_threshold,
        "count": len(anomalies),
        "anomalies": anomalies,
    }


@router.get("/organizations/{organization_id}/resources/{resource_id}/metrics", dependencies=[Depends(require_org_access)])
def resource_metrics(
    organization_id: int,
    resource_id: int,
    lookback_minutes: int = 60,
    limit: int = 100,
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

    from app.models.infrastructure_metric import InfrastructureMetric

    since = datetime.now(timezone.utc) - timedelta(minutes=max(1, min(lookback_minutes, 1440)))
    metrics = db.scalars(
        select(InfrastructureMetric)
        .where(
            InfrastructureMetric.organization_id == organization_id,
            InfrastructureMetric.resource_id == resource_id,
            InfrastructureMetric.timestamp >= since,
        )
        .order_by(InfrastructureMetric.timestamp.desc())
        .limit(max(1, min(limit, 500)))
    ).all()

    return {
        "resource_id": resource_id,
        "lookback_minutes": lookback_minutes,
        "count": len(metrics),
        "metrics": [
            {
                "id": metric.id,
                "namespace": metric.namespace,
                "metric_name": metric.metric_name,
                "dimensions": metric.dimensions,
                "timestamp": metric.timestamp,
                "value": metric.value,
                "unit": metric.unit,
                "statistic": metric.statistic,
            }
            for metric in metrics
        ],
    }


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
