from datetime import datetime, timedelta, timezone

from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.aws_account import AWSAccount
from app.models.infrastructure_graph import InfrastructureResource
from app.models.infrastructure_metric import InfrastructureMetric
from app.services.aws_credentials import build_account_session


DEFAULT_METRICS = {
    "AWS/EC2": ["CPUUtilization", "NetworkIn", "NetworkOut"],
    "AWS/RDS": ["CPUUtilization", "DatabaseConnections"],
}


def collect_cloudwatch_metrics(
    db: Session,
    account: AWSAccount,
    encryption_key: str,
    *,
    lookback_minutes: int = 15,
) -> int:
    session = build_account_session(account, encryption_key)
    client = session.client("cloudwatch", region_name=account.region)

    end = datetime.now(timezone.utc)
    start = end - timedelta(minutes=max(5, min(lookback_minutes, 60)))
    inserted = 0

    resources = db.scalars(
        select(InfrastructureResource).where(
            InfrastructureResource.organization_id == account.organization_id,
            InfrastructureResource.aws_account_id == account.id,
        )
    ).all()

    for resource in resources:
        namespace = None
        dimension_name = None
        if resource.resource_type in {"AWS::EC2::Instance", "EC2"}:
            namespace, dimension_name = "AWS/EC2", "InstanceId"
        elif resource.resource_type in {"AWS::RDS::DBInstance", "RDS"}:
            namespace, dimension_name = "AWS/RDS", "DBInstanceIdentifier"
        if not namespace or not dimension_name:
            continue

        for metric_name in DEFAULT_METRICS[namespace]:
            try:
                response = client.get_metric_statistics(
                    Namespace=namespace,
                    MetricName=metric_name,
                    Dimensions=[{"Name": dimension_name, "Value": resource.resource_id}],
                    StartTime=start,
                    EndTime=end,
                    Period=300,
                    Statistics=["Average"],
                )
            except (BotoCoreError, ClientError):
                continue

            for point in response.get("Datapoints", []):
                timestamp = point.get("Timestamp")
                value = point.get("Average")
                if timestamp is None or value is None:
                    continue

                existing = db.scalar(
                    select(InfrastructureMetric.id).where(
                        InfrastructureMetric.aws_account_id == account.id,
                        InfrastructureMetric.resource_id == resource.id,
                        InfrastructureMetric.metric_name == metric_name,
                        InfrastructureMetric.timestamp == timestamp,
                    )
                )
                if existing:
                    continue

                db.add(
                    InfrastructureMetric(
                        organization_id=account.organization_id,
                        aws_account_id=account.id,
                        resource_id=resource.id,
                        namespace=namespace,
                        metric_name=metric_name,
                        dimensions={dimension_name: resource.resource_id},
                        timestamp=timestamp,
                        value=float(value),
                        unit=point.get("Unit"),
                        statistic="Average",
                    )
                )
                inserted += 1

    if inserted:
        db.commit()
    return inserted
