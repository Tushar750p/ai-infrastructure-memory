"use client";

import { useEffect, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

export default function ReportsPage() {
  const [organizationId, setOrganizationId] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [events, setEvents] = useState<any[]>([]);
  const [incidents, setIncidents] = useState<any[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setOrganizationId(window.sessionStorage.getItem("aime.organizationId") || "");
    setApiKey(window.sessionStorage.getItem("aime.apiKey") || "");
  }, []);

  async function loadReport() {
    if (!organizationId) {
      setError("Connect or select an organization in AIME Console first.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const headers = new Headers();
      if (apiKey) headers.set("X-AIME-API-Key", apiKey);
      const [eventsResponse, incidentsResponse] = await Promise.all([
        fetch(API_BASE + "/api/organizations/" + organizationId + "/events?limit=100", { headers, credentials: "include", cache: "no-store" }),
        fetch(API_BASE + "/api/organizations/" + organizationId + "/incidents?limit=50", { headers, credentials: "include", cache: "no-store" }),
      ]);
      if (!eventsResponse.ok || !incidentsResponse.ok) throw new Error("Unable to load the organization report.");
      const eventData = await eventsResponse.json();
      const incidentData = await incidentsResponse.json();
      setEvents(eventData.events || []);
      setIncidents(incidentData.incidents || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load report");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ minHeight: "100vh", background: "#050b14", color: "#e2e8f0", padding: "34px 20px", fontFamily: "Arial, sans-serif" }}>
      <div style={{ maxWidth: 1100, margin: "0 auto" }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 16, alignItems: "center", flexWrap: "wrap" }}>
          <div>
            <div style={{ color: "#38bdf8", fontSize: 12, fontWeight: 800, letterSpacing: ".12em" }}>AIME · SRE REPORTS</div>
            <h1 style={{ fontSize: 34, margin: "8px 0 4px" }}>Infrastructure & Incident Report</h1>
            <p style={{ color: "#94a3b8", margin: 0 }}>A production-safe reporting surface built from AIME's real infrastructure memory APIs.</p>
          </div>
          <button onClick={() => window.print()} style={{ padding: "11px 16px", borderRadius: 9, border: "1px solid #334155", background: "#0f1d30", color: "#e2e8f0", fontWeight: 700 }}>Print / Save PDF</button>
        </div>

        <section style={{ marginTop: 24, padding: 18, borderRadius: 12, border: "1px solid #1e293b", background: "#0b1422" }}>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <input value={organizationId} onChange={(e) => setOrganizationId(e.target.value)} placeholder="Organization ID" style={{ flex: "1 1 220px", minWidth: 220, background: "#08111e", border: "1px solid #334155", borderRadius: 8, padding: "11px 13px", color: "#fff" }} />
            <button onClick={loadReport} disabled={loading} style={{ padding: "11px 18px", borderRadius: 8, border: 0, background: "#38bdf8", color: "#03111d", fontWeight: 800 }}>{loading ? "Loading..." : "Generate Report"}</button>
          </div>
          {error && <p style={{ color: "#fb7185", marginBottom: 0 }}>{error}</p>}
        </section>

        <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(190px,1fr))", gap: 12, marginTop: 18 }}>
          {[
            ["Events in memory", events.length],
            ["Incidents", incidents.length],
            ["Open incidents", incidents.filter((i) => i.status === "open").length],
            ["Resolved incidents", incidents.filter((i) => i.status === "resolved").length],
          ].map(([label, value]) => (
            <div key={String(label)} style={{ padding: 18, borderRadius: 12, border: "1px solid #1e293b", background: "#0b1422" }}>
              <div style={{ color: "#64748b", fontSize: 12 }}>{label}</div>
              <div style={{ fontSize: 28, fontWeight: 800, marginTop: 6 }}>{value}</div>
            </div>
          ))}
        </section>

        <section style={{ marginTop: 18, padding: 20, borderRadius: 12, border: "1px solid #1e293b", background: "#0b1422" }}>
          <h2 style={{ marginTop: 0 }}>Incident Summary</h2>
          {incidents.length === 0 ? <p style={{ color: "#64748b" }}>No incidents loaded.</p> : incidents.slice(0, 20).map((incident) => (
            <article key={incident.id} style={{ padding: "14px 0", borderTop: "1px solid #172235" }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                <strong>{incident.title}</strong>
                <span style={{ color: incident.status === "open" ? "#fb7185" : "#4ade80", fontSize: 11, fontWeight: 800 }}>{String(incident.status || "").toUpperCase()}</span>
              </div>
              <div style={{ color: "#cbd5e1", marginTop: 5, fontSize: 13 }}>{incident.summary || "No summary available."}</div>
              <div style={{ color: "#64748b", marginTop: 5, fontSize: 11 }}>Severity: {incident.severity || "—"} · Started: {incident.started_at ? new Date(incident.started_at).toLocaleString() : "—"}</div>
              {incident.root_cause && <div style={{ color: "#a78bfa", marginTop: 5, fontSize: 12 }}>Root cause: {incident.root_cause}</div>}
            </article>
          ))}
        </section>

        <section style={{ marginTop: 18, padding: 20, borderRadius: 12, border: "1px solid #1e293b", background: "#0b1422" }}>
          <h2 style={{ marginTop: 0 }}>Recent Infrastructure Memory</h2>
          {events.length === 0 ? <p style={{ color: "#64748b" }}>No events loaded.</p> : events.slice(0, 50).map((event) => (
            <article key={event.id} style={{ padding: "13px 0", borderTop: "1px solid #172235" }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                <strong>{event.event_name || "Infrastructure event"}</strong>
                <time style={{ color: "#64748b", fontSize: 11 }}>{event.event_time ? new Date(event.event_time).toLocaleString() : "—"}</time>
              </div>
              <div style={{ color: "#94a3b8", marginTop: 5, fontSize: 12 }}>{event.summary || "Infrastructure change recorded"}</div>
              <div style={{ color: "#64748b", marginTop: 5, fontSize: 10 }}>Account: {event.aws_account_id ?? "—"} · Region: {event.region || "—"} · Resource: {event.resource_id || "—"} · Actor: {event.actor || "—"}</div>
            </article>
          ))}
        </section>
      </div>
    </main>
  );
}
