from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.infrastructure_metric import InfrastructureMetric


def detect_metric_anomalies(
    db: Session,
    *,
    organization_id: int,
    resource_id: int,
    lookback_minutes: int = 60,
    baseline_minutes: int = 360,
    z_threshold: float = 2.5,
    limit: int = 50,
) -> list[dict]:
    now = datetime.now(timezone.utc)
    lookback_start = now - timedelta(minutes=max(1, min(lookback_minutes, 1440)))
    baseline_start = lookback_start - timedelta(minutes=max(30, min(baseline_minutes, 7 * 24 * 60)))

    metrics = db.scalars(
        select(InfrastructureMetric)
        .where(
            InfrastructureMetric.organization_id == organization_id,
            InfrastructureMetric.resource_id == resource_id,
            InfrastructureMetric.timestamp >= baseline_start,
        )
        .order_by(InfrastructureMetric.timestamp.asc())
    ).all()

    by_metric: dict[str, list[InfrastructureMetric]] = {}
    for metric in metrics:
        by_metric.setdefault(metric.metric_name, []).append(metric)

    anomalies = []
    for metric_name, points in by_metric.items():
        baseline = [p.value for p in points if p.timestamp < lookback_start]
        recent = [p for p in points if p.timestamp >= lookback_start]
        if len(baseline) < 3 or not recent:
            continue

        mean = sum(baseline) / len(baseline)
        variance = sum((value - mean) ** 2 for value in baseline) / len(baseline)
        stddev = variance ** 0.5

        for point in recent:
            if stddev > 0:
                z_score = abs(point.value - mean) / stddev
            else:
                z_score = 0.0 if point.value == mean else float("inf")

            if z_score >= z_threshold:
                anomalies.append({
                    "metric_id": point.id,
                    "metric_name": point.metric_name,
                    "timestamp": point.timestamp,
                    "value": point.value,
                    "baseline_mean": round(mean, 4),
                    "baseline_stddev": round(stddev, 4),
                    "z_score": round(z_score, 3) if z_score != float("inf") else None,
                    "unit": point.unit,
                    "severity": "high" if z_score >= z_threshold * 1.5 else "medium",
                })

    anomalies.sort(key=lambda item: item["timestamp"], reverse=True)
    return anomalies[: max(1, min(limit, 200))]
