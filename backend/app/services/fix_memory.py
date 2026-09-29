import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.infrastructure_fix import InfrastructureFix
from app.models.infrastructure_incident import InfrastructureIncident
from app.models.infrastructure_graph import InfrastructureResource


def _tokens(value: str | None) -> set[str]:
    if not value:
        return set()
    return {
        token for token in re.findall(r"[a-z0-9_-]{3,}", value.lower())
        if token not in {"the", "and", "for", "with", "from", "this", "that"}
    }


def find_similar_fixes(
    db: Session,
    incident: InfrastructureIncident,
    *,
    limit: int = 5,
) -> list[dict]:
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

    query_text = " ".join(
        value for value in (
            incident.title,
            incident.summary,
            incident.root_cause,
        )
        if value
    )
    query_tokens = _tokens(query_text)

    fixes = db.scalars(
        select(InfrastructureFix)
        .where(
            InfrastructureFix.organization_id == incident.organization_id,
            InfrastructureFix.incident_id != incident.id,
            InfrastructureFix.verified.is_(True),
        )
        .order_by(InfrastructureFix.created_at.desc())
        .limit(200)
    ).all()

    ranked = []
    for fix in fixes:
        related_incident = db.get(InfrastructureIncident, fix.incident_id)
        if not related_incident:
            continue

        related_resource = (
            db.get(InfrastructureResource, fix.resource_id)
            if fix.resource_id
            else None
        )
        fix_text = " ".join(
            value for value in (
                fix.title,
                fix.resolution,
                fix.outcome,
                related_incident.title,
                related_incident.summary,
                related_incident.root_cause,
            )
            if value
        )
        fix_tokens = _tokens(fix_text)
        overlap = len(query_tokens & fix_tokens)
        score = overlap / max(1, len(query_tokens))

        if resource and related_resource and resource.resource_type == related_resource.resource_type:
            score += 0.35
        if resource and related_resource and resource.region == related_resource.region:
            score += 0.10

        if score > 0:
            ranked.append((score, fix, related_incident, related_resource))

    ranked.sort(key=lambda item: (item[0], item[1].created_at), reverse=True)

    return [
        {
            "fix_id": fix.id,
            "incident_id": fix.incident_id,
            "title": fix.title,
            "resolution": fix.resolution,
            "commands": fix.commands,
            "steps": fix.steps,
            "outcome": fix.outcome,
            "verified": fix.verified,
            "similarity_score": round(min(score, 1.0), 3),
            "matched_resource_type": related_resource.resource_type if related_resource else None,
            "created_at": fix.created_at,
        }
        for score, fix, _, related_resource in ranked[: max(1, min(limit, 20))]
    ]
