from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.aws_account import AWSAccount
from app.models.infrastructure_graph import InfrastructureRelationship, InfrastructureResource
from app.services.aws_credentials import build_aws_session, decrypt_secret


def _upsert_resource(
    db: Session,
    account: AWSAccount,
    resource_type: str,
    resource_id: str,
    *,
    name: str | None = None,
    region: str | None = None,
    status: str = "active",
) -> InfrastructureResource:
    resource = db.scalar(
        select(InfrastructureResource).where(
            InfrastructureResource.aws_account_id == account.id,
            InfrastructureResource.resource_type == resource_type,
            InfrastructureResource.resource_id == resource_id,
        )
    )
    if resource:
        resource.name = name or resource.name
        resource.region = region or resource.region
        resource.status = status
        return resource

    resource = InfrastructureResource(
        organization_id=account.organization_id,
        aws_account_id=account.id,
        resource_type=resource_type,
        resource_id=resource_id,
        name=name,
        region=region or account.region,
        status=status,
    )
    db.add(resource)
    db.flush()
    return resource


def _link(
    db: Session,
    account: AWSAccount,
    source: InfrastructureResource,
    target: InfrastructureResource,
    relationship_type: str,
) -> None:
    if source.id == target.id:
        return
    existing = db.scalar(
        select(InfrastructureRelationship).where(
            InfrastructureRelationship.source_resource_id == source.id,
            InfrastructureRelationship.target_resource_id == target.id,
            InfrastructureRelationship.relationship_type == relationship_type,
        )
    )
    if not existing:
        db.add(
            InfrastructureRelationship(
                organization_id=account.organization_id,
                source_resource_id=source.id,
                target_resource_id=target.id,
                relationship_type=relationship_type,
            )
        )


def sync_aws_inventory(db: Session, account: AWSAccount, encryption_key: str) -> int:
    access_key_id = decrypt_secret(account.encrypted_access_key_id, encryption_key)
    secret_access_key = decrypt_secret(account.encrypted_secret_access_key, encryption_key)
    session = build_aws_session(access_key_id, secret_access_key, account.region)

    discovered = 0

    try:
        ec2 = session.client("ec2", region_name=account.region)
        vpcs: dict[str, InfrastructureResource] = {}
        subnets: dict[str, InfrastructureResource] = {}
        security_groups: dict[str, InfrastructureResource] = {}

        for page in ec2.get_paginator("describe_vpcs").paginate():
            for item in page.get("Vpcs", []):
                vpc_id = item["VpcId"]
                vpcs[vpc_id] = _upsert_resource(
                    db, account, "ec2.vpc", vpc_id, region=account.region
                )
                discovered += 1

        for page in ec2.get_paginator("describe_subnets").paginate():
            for item in page.get("Subnets", []):
                subnet_id = item["SubnetId"]
                subnet = _upsert_resource(
                    db,
                    account,
                    "ec2.subnet",
                    subnet_id,
                    name=item.get("Tags", [{}])[0].get("Value") if item.get("Tags") else None,
                    region=item.get("AvailabilityZone", account.region)[:-1],
                )
                subnets[subnet_id] = subnet
                discovered += 1
                vpc = vpcs.get(item.get("VpcId"))
                if vpc:
                    _link(db, account, subnet, vpc, "part_of")

        for page in ec2.get_paginator("describe_security_groups").paginate():
            for item in page.get("SecurityGroups", []):
                group_id = item["GroupId"]
                group = _upsert_resource(
                    db,
                    account,
                    "ec2.security_group",
                    group_id,
                    name=item.get("GroupName"),
                    region=account.region,
                )
                security_groups[group_id] = group
                discovered += 1

        for page in ec2.get_paginator("describe_instances").paginate():
            for reservation in page.get("Reservations", []):
                for item in reservation.get("Instances", []):
                    instance_id = item.get("InstanceId")
                    if not instance_id:
                        continue
                    tags = {tag["Key"]: tag["Value"] for tag in item.get("Tags", [])}
                    instance = _upsert_resource(
                        db,
                        account,
                        "ec2.instance",
                        instance_id,
                        name=tags.get("Name"),
                        region=item.get("Placement", {}).get("AvailabilityZone", account.region)[:-1],
                        status=item.get("State", {}).get("Name", "unknown"),
                    )
                    discovered += 1

                    subnet = subnets.get(item.get("SubnetId"))
                    if subnet:
                        _link(db, account, instance, subnet, "located_in")

                    for group in item.get("SecurityGroups", []):
                        security_group = security_groups.get(group.get("GroupId"))
                        if security_group:
                            _link(db, account, instance, security_group, "uses_security_group")

        rds = session.client("rds", region_name=account.region)
        for page in rds.get_paginator("describe_db_instances").paginate():
            for item in page.get("DBInstances", []):
                identifier = item.get("DBInstanceIdentifier")
                if not identifier:
                    continue
                db_instance = _upsert_resource(
                    db,
                    account,
                    "rds.db_instance",
                    identifier,
                    name=identifier,
                    region=account.region,
                    status=item.get("DBInstanceStatus", "unknown"),
                )
                discovered += 1

                subnet_group = item.get("DBSubnetGroup") or {}
                vpc = vpcs.get(subnet_group.get("VpcId"))
                if vpc:
                    _link(db, account, db_instance, vpc, "located_in")

                for group in item.get("VpcSecurityGroups", []):
                    security_group = security_groups.get(group.get("VpcSecurityGroupId"))
                    if security_group:
                        _link(db, account, db_instance, security_group, "uses_security_group")

        cache = session.client("elasticache", region_name=account.region)
        for page in cache.get_paginator("describe_replication_groups").paginate():
            for item in page.get("ReplicationGroups", []):
                identifier = item.get("ReplicationGroupId")
                if not identifier:
                    continue
                redis = _upsert_resource(
                    db,
                    account,
                    "elasticache.replication_group",
                    identifier,
                    name=identifier,
                    region=account.region,
                    status=item.get("Status", "unknown"),
                )
                discovered += 1
                for group in item.get("SecurityGroups", []):
                    group_id = group.get("SecurityGroupId")
                    security_group = security_groups.get(group_id)
                    if security_group:
                        _link(db, account, redis, security_group, "uses_security_group")

        db.commit()
    except (BotoCoreError, ClientError):
        db.rollback()
        raise

    return discovered
