from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.infrastructure_event import InfrastructureEvent
from app.models.infrastructure_graph import InfrastructureRelationship, InfrastructureResource


def build_root_cause_analysis(
    db: Session,
    resource: InfrastructureResource,
    *,
    lookback_minutes: int = 60,
    limit: int = 50,
) -> dict:
    now = datetime.now(timezone.utc)
    since = now - timedelta(minutes=max(1, min(lookback_minutes, 1440)))

    related_ids = db.scalars(
        select(InfrastructureResource.id)
        .join(
            InfrastructureRelationship,
            or_(
                InfrastructureRelationship.source_resource_id == InfrastructureResource.id,
                InfrastructureRelationship.target_resource_id == InfrastructureResource.id,
            ),
        )
        .where(
            InfrastructureRelationship.organization_id == resource.organization_id,
            or_(
                InfrastructureRelationship.source_resource_id == resource.id,
                InfrastructureRelationship.target_resource_id == resource.id,
            ),
        )
    ).all()

    related_resources = db.scalars(
        select(InfrastructureResource).where(InfrastructureResource.id.in_(related_ids))
    ).all() if related_ids else []

    resource_ids = {resource.resource_id}
    resource_ids.update(item.resource_id for item in related_resources if item.resource_id)

    conditions = [InfrastructureEvent.resource_id == value for value in resource_ids]
    events = db.scalars(
        select(InfrastructureEvent)
        .where(
            InfrastructureEvent.organization_id == resource.organization_id,
            InfrastructureEvent.event_time >= since,
            or_(*conditions) if conditions else False,
        )
        .order_by(InfrastructureEvent.event_time.desc())
        .limit(max(1, min(limit, 200)))
    ).all()

    high_signal_names = (
        "Modify", "Update", "Delete", "Stop", "Terminate", "Reboot",
        "Authorize", "Revoke", "Put", "Remove", "Detach", "Attach",
    )
    evidence = []
    for event in events:
        signal = any(event.event_name.startswith(prefix) for prefix in high_signal_names)
        evidence.append({
            "event_id": event.id,
            "event_name": event.event_name,
            "event_time": event.event_time,
            "resource_id": event.resource_id,
            "actor": event.actor,
            "signal": "high" if signal else "normal",
            "summary": event.summary,
        })

    high_signal = [item for item in evidence if item["signal"] == "high"]
    if high_signal:
        latest = high_signal[0]
        root_cause = (
            f"Potential change-related cause: {latest['event_name']} affected "
            f"{latest['resource_id'] or resource.resource_id} at {latest['event_time'].isoformat()}."
        )
        confidence = "evidence-backed"
    elif evidence:
        root_cause = (
            "Recent infrastructure changes were detected, but no high-signal "
            "mutation event was identified."
        )
        confidence = "low"
    else:
        root_cause = "No recent infrastructure change evidence was found in the selected window."
        confidence = "insufficient-evidence"

    return {
        "resource": {
            "id": resource.id,
            "type": resource.resource_type,
            "resource_id": resource.resource_id,
            "name": resource.name,
            "region": resource.region,
            "status": resource.status,
        },
        "lookback_minutes": lookback_minutes,
        "confidence": confidence,
        "root_cause": root_cause,
        "evidence": evidence,
        "related_resources": [
            {
                "id": item.id,
                "type": item.resource_type,
                "resource_id": item.resource_id,
                "name": item.name,
            }
            for item in related_resources
        ],
    }
