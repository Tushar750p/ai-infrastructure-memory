from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.infrastructure_event import InfrastructureEvent
from app.models.infrastructure_graph import InfrastructureRelationship, InfrastructureResource


def correlate_resource_changes(
    db: Session,
    resource: InfrastructureResource,
    *,
    lookback_minutes: int = 60,
    limit: int = 50,
) -> dict:
    now = datetime.now(timezone.utc)
    since = now - timedelta(minutes=max(1, min(lookback_minutes, 1440)))

    resource_id = resource.resource_id
    patterns = [resource_id]
    if resource_id.startswith("arn:"):
        patterns.append(resource_id.rsplit("/", 1)[-1])

    conditions = [
        InfrastructureEvent.resource_id == value
        for value in patterns
        if value
    ]

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
        select(InfrastructureResource).where(
            InfrastructureResource.id.in_(related_ids)
        )
    ).all() if related_ids else []

    for related in related_resources:
        if related.resource_id:
            conditions.append(InfrastructureEvent.resource_id == related.resource_id)

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
        "correlated_changes": [
            {
                "id": event.id,
                "event_id": event.event_id,
                "event_name": event.event_name,
                "event_time": event.event_time,
                "source": event.source,
                "region": event.region,
                "resource_id": event.resource_id,
                "actor": event.actor,
                "summary": event.summary,
            }
            for event in events
        ],
        "change_count": len(events),
        "analysis": (
            f"{len(events)} infrastructure change(s) were recorded around this resource "
            f"in the last {lookback_minutes} minutes."
            if events
            else "No matching infrastructure changes were recorded in the selected window."
        ),
    }
