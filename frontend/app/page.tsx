"use client";

import { useEffect, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type EventItem = {
  id: number;
  aws_account_id: number;
  event_id: string;
  source: string;
  event_name: string;
  event_time: string;
  region?: string;
  resource_type?: string;
  resource_id?: string;
  actor?: string;
  summary?: string;
};

export default function Home() {
  const [organizationId, setOrganizationId] = useState("");
  const [events, setEvents] = useState<EventItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [orgName, setOrgName] = useState("");
  const [accessKey, setAccessKey] = useState("");
  const [secretKey, setSecretKey] = useState("");
  const [region, setRegion] = useState("us-east-1");
  const [connecting, setConnecting] = useState(false);
  const [connectMessage, setConnectMessage] = useState("");

  async function loadEvents() {
    if (!organizationId) return;
    setLoading(true);
    setError("");
    try {
      const response = await fetch(
        API_BASE + "/api/organizations/" + organizationId + "/events?limit=100",
        { cache: "no-store" },
      );
      if (!response.ok) throw new Error("API returned " + response.status);
      const data = await response.json();
      setEvents(data.events || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load events");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (organizationId) loadEvents();
  }, [organizationId]);

  async function connectAwsAccount() {
    setConnecting(true);
    setConnectMessage("");
    setError("");
    try {
      const response = await fetch(API_BASE + "/api/aws/accounts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          organization_name: orgName,
          access_key_id: accessKey,
          secret_access_key: secretKey,
          region,
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "AWS connection failed");
      setOrganizationId(String(data.organization_id));
      setConnectMessage("AWS account connected successfully.");
      setAccessKey("");
      setSecretKey("");
      setOrgName("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "AWS connection failed");
    } finally {
      setConnecting(false);
    }
  }

  return (
    <main style={{ minHeight: "100vh", background: "#07111f", color: "#e2e8f0", padding: "40px", fontFamily: "Arial, sans-serif" }}>
      <div style={{ maxWidth: 1200, margin: "0 auto" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 20, flexWrap: "wrap" }}>
          <div>
            <p style={{ color: "#38bdf8", fontSize: 13, letterSpacing: 2, fontWeight: 700 }}>AIME CONSOLE</p>
            <h1 style={{ fontSize: 36, margin: "6px 0" }}>Infrastructure Memory</h1>
            <p style={{ color: "#94a3b8" }}>Your infrastructure remembers every change.</p>
          </div>
          <div style={{ display: "flex", gap: 10 }}>
            <input value={organizationId} onChange={(e) => setOrganizationId(e.target.value.replace(/\D/g, ""))} placeholder="Organization ID" style={{ background: "#0f1d30", border: "1px solid #334155", borderRadius: 8, padding: "11px 14px", color: "#fff", width: 150 }} />
            <button onClick={loadEvents} style={{ background: "#0284c7", border: 0, borderRadius: 8, padding: "11px 18px", color: "#fff", fontWeight: 700, cursor: "pointer" }}>Refresh Memory</button>
          </div>
        </div>

        <section style={{ marginTop: 32, background: "#0b1728", border: "1px solid #1e293b", borderRadius: 14, padding: 22 }}>
          <h2 style={{ marginTop: 0 }}>Connect AWS Account</h2>
          <p style={{ color: "#64748b" }}>Credentials are sent only to the backend for STS verification and encrypted storage.</p>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 12 }}>
            <input value={orgName} onChange={(e) => setOrgName(e.target.value)} placeholder="Organization name" style={inputStyle} />
            <input value={region} onChange={(e) => setRegion(e.target.value)} placeholder="AWS region" style={inputStyle} />
            <input value={accessKey} onChange={(e) => setAccessKey(e.target.value)} placeholder="AWS Access Key ID" autoComplete="off" style={inputStyle} />
            <input value={secretKey} onChange={(e) => setSecretKey(e.target.value)} placeholder="AWS Secret Access Key" type="password" autoComplete="new-password" style={inputStyle} />
          </div>
          <button onClick={connectAwsAccount} disabled={connecting || !orgName || !accessKey || !secretKey} style={{ marginTop: 14, background: "#16a34a", border: 0, borderRadius: 8, padding: "11px 18px", color: "#fff", fontWeight: 700, cursor: "pointer", opacity: connecting ? 0.6 : 1 }}>
            {connecting ? "Verifying AWS..." : "Connect AWS"}
          </button>
          {connectMessage && <p style={{ color: "#4ade80" }}>{connectMessage}</p>}
        </section>

        <section style={{ marginTop: 32, display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
          <Metric title="Events in Memory" value={events.length.toString()} />
          <Metric title="Latest Source" value={events[0]?.source || "—"} />
          <Metric title="Latest Region" value={events[0]?.region || "—"} />
        </section>

        <section style={{ marginTop: 28, background: "#0b1728", border: "1px solid #1e293b", borderRadius: 14, overflow: "hidden" }}>
          <div style={{ padding: "20px 22px", borderBottom: "1px solid #1e293b" }}>
            <h2 style={{ margin: 0 }}>Infrastructure Timeline</h2>
            <p style={{ color: "#64748b", marginBottom: 0 }}>Events collected from AWS CloudTrail.</p>
          </div>
          {loading && <p style={{ padding: 24, color: "#38bdf8" }}>Loading infrastructure memory...</p>}
          {error && <p style={{ padding: 24, color: "#fb7185" }}>Connection error: {error}</p>}
          {!loading && !error && organizationId && events.length === 0 && <p style={{ padding: 24, color: "#94a3b8" }}>No events found for this organization.</p>}
          {!organizationId && <p style={{ padding: 24, color: "#94a3b8" }}>Enter an organization ID to view infrastructure memory.</p>}
          {events.map((event) => (
            <article key={event.id} style={{ padding: "18px 22px", borderTop: "1px solid #172235" }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 20 }}>
                <div>
                  <strong style={{ fontSize: 16 }}>{event.event_name}</strong>
                  <div style={{ color: "#94a3b8", marginTop: 6 }}>{event.summary || "Infrastructure change recorded"}</div>
                </div>
                <time style={{ color: "#64748b", fontSize: 13 }}>{new Date(event.event_time).toLocaleString()}</time>
              </div>
              <div style={{ display: "flex", gap: 18, flexWrap: "wrap", marginTop: 12, color: "#7dd3fc", fontSize: 13 }}>
                <span>Account: {event.aws_account_id}</span>
                <span>Region: {event.region || "—"}</span>
                <span>Resource: {event.resource_id || "—"}</span>
                <span>Actor: {event.actor || "—"}</span>
              </div>
            </article>
          ))}
        </section>
      </div>
    </main>
  );
}

const inputStyle = { background: "#0f1d30", border: "1px solid #334155", borderRadius: 8, padding: "11px 14px", color: "#fff", width: "100%", boxSizing: "border-box" as const };

function Metric({ title, value }: { title: string; value: string }) {
  return (
    <div style={{ background: "#0b1728", border: "1px solid #1e293b", borderRadius: 12, padding: 20 }}>
      <div style={{ color: "#64748b", fontSize: 13 }}>{title}</div>
      <div style={{ marginTop: 8, fontSize: 22, fontWeight: 700 }}>{value}</div>
    </div>
  );
}
