from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.infrastructure_event import InfrastructureEvent
from app.models.infrastructure_graph import InfrastructureResource
from app.models.infrastructure_incident import InfrastructureIncident
from app.models.infrastructure_metric import InfrastructureMetric
from app.services.anomaly_detection import detect_metric_anomalies

HIGH_SIGNAL_PREFIXES = (
    "Modify", "Update", "Delete", "Stop", "Terminate", "Reboot",
    "Authorize", "Revoke", "Put", "Remove", "Detach", "Attach",
)


def detect_incidents_for_account(
    db: Session,
    *,
    organization_id: int,
    aws_account_id: int,
    lookback_minutes: int = 15,
) -> int:
    now = datetime.now(timezone.utc)
    since = now - timedelta(minutes=max(1, min(lookback_minutes, 120)))

    events = db.scalars(
        select(InfrastructureEvent)
        .where(
            InfrastructureEvent.organization_id == organization_id,
            InfrastructureEvent.aws_account_id == aws_account_id,
            InfrastructureEvent.event_time >= since,
        )
        .order_by(InfrastructureEvent.event_time.desc())
    ).all()

    created = 0
    for event in events:
        if not any(event.event_name.startswith(prefix) for prefix in HIGH_SIGNAL_PREFIXES):
            continue

        resource = None
        if event.resource_id:
            resource = db.scalar(
                select(InfrastructureResource).where(
                    InfrastructureResource.organization_id == organization_id,
                    InfrastructureResource.aws_account_id == aws_account_id,
                    InfrastructureResource.resource_id == event.resource_id,
                )
            )

        existing = db.scalar(
            select(InfrastructureIncident.id).where(
                InfrastructureIncident.organization_id == organization_id,
                InfrastructureIncident.aws_account_id == aws_account_id,
                InfrastructureIncident.started_at == event.event_time,
                InfrastructureIncident.summary == event.summary,
            )
        )
        if existing:
            continue

        metric_evidence = []
        anomaly_evidence = []
        if resource:
            anomaly_evidence = detect_metric_anomalies(
                db,
                organization_id=organization_id,
                resource_id=resource.id,
                lookback_minutes=lookback_minutes,
                baseline_minutes=360,
                z_threshold=2.5,
                limit=20,
            )

            metrics = db.scalars(
                select(InfrastructureMetric)
                .where(
                    InfrastructureMetric.organization_id == organization_id,
                    InfrastructureMetric.resource_id == resource.id,
                    InfrastructureMetric.timestamp >= since,
                )
                .order_by(InfrastructureMetric.timestamp.desc())
                .limit(20)
            ).all()
            for metric in metrics:
                metric_evidence.append({
                    "metric_name": metric.metric_name,
                    "timestamp": metric.timestamp.isoformat(),
                    "value": metric.value,
                    "unit": metric.unit,
                    "statistic": metric.statistic,
                })

        incident = InfrastructureIncident(
            organization_id=organization_id,
            aws_account_id=aws_account_id,
            resource_id=resource.id if resource else None,
            title=f"Change detected: {event.event_name}",
            severity="medium",
            status="open",
            started_at=event.event_time,
            summary=(
                f"High-signal infrastructure change detected for "
                f"{event.resource_id or 'unknown resource'}."
            ),
            evidence=[{
                "type": "change",
                "event_id": event.id,
                "event_name": event.event_name,
                "event_time": event.event_time.isoformat(),
                "resource_id": event.resource_id,
                "actor": event.actor,
                "summary": event.summary,
            }, {
                "type": "telemetry",
                "metrics": metric_evidence,
                "anomalies": anomaly_evidence,
            }],
        )
        db.add(incident)
        created += 1

    if created:
        db.commit()

    return created
