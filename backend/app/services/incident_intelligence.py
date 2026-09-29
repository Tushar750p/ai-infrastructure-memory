
def build_incident_intelligence(timeline: dict) -> dict:
    items = timeline.get("timeline", [])
    changes = [item for item in items if item.get("type") == "change"]
    anomalies = [item for item in items if item.get("type") == "anomaly"]
    fixes = [item for item in items if item.get("type") == "fix"]
    resolved = any(item.get("type") == "resolved" for item in items)

    score = 0
    reasons = []

    if changes:
        score += 30
        reasons.append(f"{len(changes)} infrastructure change(s) detected")
    if anomalies:
        score += 35
        reasons.append(f"{len(anomalies)} metric anomal{'' if len(anomalies) == 1 else 'ies'} detected")
    if changes and anomalies:
        score += 20
        reasons.append("change and telemetry anomaly are both present")
    if fixes:
        score += 10
        reasons.append(f"{len(fixes)} remediation record(s) available")
    if resolved:
        score += 5
        reasons.append("incident has a recorded resolution")

    score = min(score, 100)

    if score >= 75:
        confidence = "high"
    elif score >= 45:
        confidence = "medium"
    else:
        confidence = "low"

    if changes and anomalies:
        summary = (
            "A configuration or infrastructure change was recorded in the incident window "
            "and correlated telemetry anomalies were observed on the affected resource. "
            "This provides stronger evidence of a change-impact relationship, but does not "
            "by itself prove causation."
        )
    elif changes:
        summary = (
            "Infrastructure changes were detected around the incident window, but telemetry "
            "evidence is limited or absent."
        )
    elif anomalies:
        summary = (
            "Telemetry anomalies were detected, but no matching infrastructure change was "
            "identified in the available incident window."
        )
    else:
        summary = "Insufficient change and telemetry evidence is available for a strong incident explanation."

    return {
        "score": score,
        "confidence": confidence,
        "summary": summary,
        "evidence_reasons": reasons,
        "counts": {
            "changes": len(changes),
            "anomalies": len(anomalies),
            "fixes": len(fixes),
            "resolved": resolved,
        },
    }
