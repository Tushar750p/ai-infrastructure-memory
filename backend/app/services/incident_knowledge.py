from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.incident_knowledge_edge import IncidentKnowledgeEdge
from app.models.infrastructure_event import InfrastructureEvent
from app.models.infrastructure_fix import InfrastructureFix
from app.models.infrastructure_incident import InfrastructureIncident
from app.models.infrastructure_metric import InfrastructureMetric
from app.models.infrastructure_graph import InfrastructureResource


def build_incident_knowledge_graph(
    db: Session,
    incident: InfrastructureIncident,
    *,
    lookback_minutes: int = 120,
) -> dict:
    edges = []

    def add_edge(entity_type: str, entity_id: int, relationship_type: str) -> None:
        existing = db.scalar(
            select(IncidentKnowledgeEdge.id).where(
                IncidentKnowledgeEdge.organization_id == incident.organization_id,
                IncidentKnowledgeEdge.incident_id == incident.id,
                IncidentKnowledgeEdge.entity_type == entity_type,
                IncidentKnowledgeEdge.entity_id == entity_id,
                IncidentKnowledgeEdge.relationship_type == relationship_type,
            )
        )
        if not existing:
            db.add(
                IncidentKnowledgeEdge(
                    organization_id=incident.organization_id,
                    incident_id=incident.id,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    relationship_type=relationship_type,
                )
            )
        edges.append({
            "entity_type": entity_type,
            "entity_id": entity_id,
            "relationship": relationship_type,
        })

    if incident.resource_id:
        add_edge("resource", incident.resource_id, "affected_resource")

    if incident.resource_id:
        events = db.scalars(
            select(InfrastructureEvent)
            .where(
                InfrastructureEvent.organization_id == incident.organization_id,
                InfrastructureEvent.resource_id == db.scalar(
                    select(InfrastructureResource.resource_id).where(
                        InfrastructureResource.id == incident.resource_id
                    )
                ),
            )
            .order_by(InfrastructureEvent.event_time.desc())
            .limit(50)
        ).all()
        for event in events:
            add_edge("event", event.id, "change_evidence")

        anomalies = db.scalars(
            select(InfrastructureMetric)
            .where(
                InfrastructureMetric.organization_id == incident.organization_id,
                InfrastructureMetric.resource_id == incident.resource_id,
            )
            .order_by(InfrastructureMetric.timestamp.desc())
            .limit(100)
        ).all()
        for metric in anomalies:
            add_edge("metric", metric.id, "telemetry_evidence")

    fixes = db.scalars(
        select(InfrastructureFix).where(
            InfrastructureFix.organization_id == incident.organization_id,
            InfrastructureFix.incident_id == incident.id,
        )
    ).all()
    for fix in fixes:
        add_edge("fix", fix.id, "remediation")

    if edges:
        db.commit()

    return {
        "incident_id": incident.id,
        "count": len(edges),
        "edges": edges,
        "analysis": "Incident knowledge graph connects the incident to its affected resource, change evidence, telemetry evidence, and recorded remediation.",
    }
