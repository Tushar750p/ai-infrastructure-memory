from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.infrastructure_event import InfrastructureEvent
from app.models.infrastructure_fix import InfrastructureFix
from app.models.infrastructure_graph import InfrastructureResource
from app.models.infrastructure_incident import InfrastructureIncident
from app.services.anomaly_detection import detect_metric_anomalies


def build_incident_timeline(
    db: Session,
    incident: InfrastructureIncident,
    *,
    lookback_minutes: int = 120,
    limit: int = 100,
) -> dict:
    start = incident.started_at - timedelta(minutes=max(1, min(lookback_minutes, 1440)))
    end = (
        incident.resolved_at + timedelta(minutes=15)
        if incident.resolved_at
        else datetime.now(timezone.utc)
    )

    resource = (
        db.scalar(
            select(InfrastructureResource).where(
                InfrastructureResource.id == incident.resource_id,
                InfrastructureResource.organization_id == incident.organization_id,
            )
        )
        if incident.resource_id
        else None
    )

    resource_ids = {resource.resource_id} if resource and resource.resource_id else set()

    events = []
    if resource_ids:
        db_events = db.scalars(
            select(InfrastructureEvent)
            .where(
                InfrastructureEvent.organization_id == incident.organization_id,
                InfrastructureEvent.event_time >= start,
                InfrastructureEvent.event_time <= end,
                InfrastructureEvent.resource_id.in_(resource_ids),
            )
            .order_by(InfrastructureEvent.event_time.asc())
            .limit(max(1, min(limit, 500)))
        ).all()

        events.extend(
            {
                "timestamp": event.event_time,
                "type": "change",
                "severity": "high" if event.event_name.startswith(
                    ("Modify", "Update", "Delete", "Stop", "Terminate", "Reboot")
                ) else "normal",
                "title": event.event_name,
                "resource_id": event.resource_id,
                "summary": event.summary,
                "actor": event.actor,
            }
            for event in db_events
        )

    if resource:
        anomalies = detect_metric_anomalies(
            db,
            organization_id=incident.organization_id,
            resource_id=resource.id,
            lookback_minutes=max(1, int((end - start).total_seconds() / 60)),
            baseline_minutes=360,
            z_threshold=2.5,
            limit=100,
        )
        for anomaly in anomalies:
            if start <= anomaly["timestamp"] <= end:
                events.append({
                    "timestamp": anomaly["timestamp"],
                    "type": "anomaly",
                    "severity": anomaly["severity"],
                    "title": f"Metric anomaly: {anomaly['metric_name']}",
                    "resource_id": resource.resource_id,
                    "summary": (
                        f"Value {anomaly['value']} vs baseline mean "
                        f"{anomaly['baseline_mean']} (z={anomaly['z_score']})."
                    ),
                    "metric_name": anomaly["metric_name"],
                })

    fixes = db.scalars(
        select(InfrastructureFix)
        .where(
            InfrastructureFix.organization_id == incident.organization_id,
            InfrastructureFix.incident_id == incident.id,
        )
        .order_by(InfrastructureFix.created_at.asc())
    ).all()

    for fix in fixes:
        events.append({
            "timestamp": fix.created_at,
            "type": "fix",
            "severity": "resolved" if fix.verified else "normal",
            "title": fix.title,
            "resource_id": resource.resource_id if resource else None,
            "summary": fix.resolution,
            "outcome": fix.outcome,
            "verified": fix.verified,
        })

    events.append({
        "timestamp": incident.started_at,
        "type": "incident",
        "severity": incident.severity,
        "title": incident.title,
        "resource_id": resource.resource_id if resource else None,
        "summary": incident.summary,
    })

    if incident.resolved_at:
        events.append({
            "timestamp": incident.resolved_at,
            "type": "resolved",
            "severity": "resolved",
            "title": "Incident resolved",
            "resource_id": resource.resource_id if resource else None,
            "summary": incident.root_cause or "Incident marked resolved.",
        })

    events.sort(key=lambda item: item["timestamp"])

    return {
        "incident": {
            "id": incident.id,
            "title": incident.title,
            "severity": incident.severity,
            "status": incident.status,
            "started_at": incident.started_at,
            "resolved_at": incident.resolved_at,
            "resource_id": incident.resource_id,
        },
        "count": len(events),
        "timeline": events[-max(1, min(limit, 200)):],
        "analysis": (
            "Timeline combines infrastructure changes, metric anomalies, incident state, "
            "and recorded remediation steps in chronological order."
        ),
    }
