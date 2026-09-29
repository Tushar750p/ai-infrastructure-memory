"use client";

import { useEffect, useMemo, useState } from "react";

type Event = {
  id?: string;
  event_name?: string;
  event_time?: string;
  resource_id?: number | string;
  resource_type?: string;
  resource_name?: string;
  actor?: string;
  account_id?: string;
  region?: string;
  details?: Record<string, unknown>;
};

type Fix = {
  id?: string;
  title?: string;
  description?: string;
  resolution?: string;
  verified?: boolean;
  created_at?: string;
  incident_id?: string;
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

async function api(path: string, options: RequestInit = {}) {
  const key = typeof window !== "undefined" ? sessionStorage.getItem("aime.apiKey") : null;
  const headers = new Headers(options.headers);
  if (key) headers.set("X-AIME-API-Key", key);
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
    credentials: "include",
  });
  if (!response.ok) throw new Error(`Request failed: ${response.status}`);
  return response.json();
}

function prettyDate(value?: string) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function Badge({ children }: { children: React.ReactNode }) {
  return <span className="rounded-full border border-slate-700 bg-slate-900 px-2.5 py-1 text-xs text-slate-300">{children}</span>;
}

export default function TimeMachinePage() {
  const [organizationId, setOrganizationId] = useState("");
  const [resourceId, setResourceId] = useState("");
  const [events, setEvents] = useState<Event[]>([]);
  const [fixes, setFixes] = useState<Fix[]>([]);
  const [rca, setRca] = useState<Record<string, unknown> | null>(null);
  const [correlation, setCorrelation] = useState<Record<string, unknown> | null>(null);
  const [anomalies, setAnomalies] = useState<Record<string, unknown> | null>(null);
  const [metrics, setMetrics] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const savedOrg = sessionStorage.getItem("aime.organizationId") ?? "";
    setOrganizationId(savedOrg);
  }, []);

  const load = async () => {
    if (!organizationId || !resourceId) {
      setError("Enter an organization ID and resource ID.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const [timeline, fixMemory, rcaData, correlationData, anomalyData, metricData] =
        await Promise.all([
          api(`/api/organizations/${organizationId}/resources/${encodeURIComponent(resourceId)}/timeline`),
          api(`/api/organizations/${organizationId}/resources/${encodeURIComponent(resourceId)}/fix-memory`),
          api(`/api/organizations/${organizationId}/resources/${encodeURIComponent(resourceId)}/rca`),
          api(`/api/organizations/${organizationId}/resources/${encodeURIComponent(resourceId)}/correlation`),
          api(`/api/organizations/${organizationId}/resources/${encodeURIComponent(resourceId)}/anomalies`),
          api(`/api/organizations/${organizationId}/resources/${encodeURIComponent(resourceId)}/metrics`),
        ]);
      setEvents(Array.isArray(timeline) ? timeline : timeline.timeline ?? timeline.events ?? []);
      setFixes(Array.isArray(fixMemory) ? fixMemory : fixMemory.fixes ?? []);
      setRca(rcaData);
      setCorrelation(correlationData);
      setAnomalies(anomalyData);
      setMetrics(metricData);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to load resource intelligence.");
      setEvents([]);
      setFixes([]);
    } finally {
      setLoading(false);
    }
  };

  const orderedEvents = useMemo(
    () => [...events].sort((a, b) => new Date(b.event_time ?? 0).getTime() - new Date(a.event_time ?? 0).getTime()),
    [events]
  );

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-7xl px-6 py-10">
        <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <div className="mb-2 text-xs font-semibold uppercase tracking-[0.25em] text-cyan-400">AIME · SRE MEMORY ENGINE</div>
            <h1 className="text-3xl font-semibold tracking-tight">Infrastructure Time Machine</h1>
            <p className="mt-2 max-w-3xl text-sm text-slate-400">
              Reconstruct what changed, when it changed, what correlated with the incident, and which verified fixes exist for the same resource.
            </p>
          </div>
          <a href="/demo" className="text-sm text-slate-400 hover:text-white">Product overview →</a>
        </div>

        <section className="mb-6 rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
          <div className="grid gap-4 md:grid-cols-[1fr_1fr_auto]">
            <label className="text-sm text-slate-300">
              Organization ID
              <input value={organizationId} onChange={(e) => setOrganizationId(e.target.value)} placeholder="org_..." className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm outline-none focus:border-cyan-500" />
            </label>
            <label className="text-sm text-slate-300">
              Resource ID
              <input value={resourceId} onChange={(e) => setResourceId(e.target.value)} placeholder="Resource ID (numeric)" className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm outline-none focus:border-cyan-500" />
            </label>
            <button onClick={load} disabled={loading} className="self-end rounded-xl bg-cyan-400 px-5 py-2.5 text-sm font-semibold text-slate-950 disabled:opacity-50">
              {loading ? "Reconstructing…" : "Reconstruct"}
            </button>
          </div>
          {error && <p className="mt-3 text-sm text-rose-400">{error}</p>}
        </section>

        <div className="grid gap-4 md:grid-cols-4">
          {[
            ["Timeline events", events.length],
            ["Known fixes", fixes.length],
            ["Correlations", Object.keys(correlation ?? {}).length],
            ["Anomaly signals", Object.keys(anomalies ?? {}).length],
          ].map(([label, value]) => (
            <div key={String(label)} className="rounded-2xl border border-slate-800 bg-slate-900/50 p-5">
              <div className="text-xs uppercase tracking-wider text-slate-500">{label}</div>
              <div className="mt-2 text-2xl font-semibold">{value}</div>
            </div>
          ))}
        </div>

        <div className="mt-6 grid gap-6 lg:grid-cols-[1.35fr_0.65fr]">
          <section className="rounded-2xl border border-slate-800 bg-slate-900/50 p-5">
            <div className="mb-5 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold">Change timeline</h2>
                <p className="text-xs text-slate-500">Infrastructure memory reconstructed from recorded events.</p>
              </div>
              <Badge>{orderedEvents.length} events</Badge>
            </div>
            <div className="space-y-4">
              {orderedEvents.length === 0 ? (
                <div className="rounded-xl border border-dashed border-slate-800 p-8 text-center text-sm text-slate-500">No timeline loaded yet.</div>
              ) : orderedEvents.map((event, index) => (
                <div key={event.id ?? `${event.event_time}-${index}`} className="relative border-l border-slate-700 pl-5">
                  <div className="absolute -left-1.5 top-1.5 h-3 w-3 rounded-full bg-cyan-400" />
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium">{event.event_name ?? "Infrastructure change"}</span>
                    {event.resource_type && <Badge>{event.resource_type}</Badge>}
                  </div>
                  <div className="mt-1 text-xs text-slate-500">{prettyDate(event.event_time)} · {event.actor ?? "unknown actor"}</div>
                  <div className="mt-2 grid gap-2 text-xs text-slate-400 md:grid-cols-3">
                    <span>Resource: {event.resource_name ?? event.resource_id ?? "—"}</span>
                    <span>Account: {event.account_id ?? "—"}</span>
                    <span>Region: {event.region ?? "—"}</span>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <div className="space-y-6">
            <section className="rounded-2xl border border-slate-800 bg-slate-900/50 p-5">
              <h2 className="text-lg font-semibold">RCA signal</h2>
              <p className="mt-1 text-xs text-slate-500">Current deterministic RCA output for this resource.</p>
              <pre className="mt-4 max-h-72 overflow-auto rounded-xl bg-slate-950 p-4 text-xs leading-5 text-cyan-100">{JSON.stringify(rca ?? {}, null, 2)}</pre>
            </section>
            <section className="rounded-2xl border border-slate-800 bg-slate-900/50 p-5">
              <h2 className="text-lg font-semibold">Correlation & anomalies</h2>
              <pre className="mt-4 max-h-72 overflow-auto rounded-xl bg-slate-950 p-4 text-xs leading-5 text-slate-300">{JSON.stringify({ correlation, anomalies, metrics }, null, 2)}</pre>
            </section>
          </div>
        </div>

        <section className="mt-6 rounded-2xl border border-slate-800 bg-slate-900/50 p-5">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold">Rollback Intelligence · Verified fix memory</h2>
              <p className="mt-1 text-xs text-slate-500">Historical fixes are evidence for investigation—not an automatic production rollback.</p>
            </div>
            <Badge>{fixes.length} remembered</Badge>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {fixes.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-800 p-6 text-sm text-slate-500 md:col-span-2">No verified fixes recorded for this resource.</div>
            ) : fixes.map((fix, index) => (
              <article key={fix.id ?? index} className="rounded-xl border border-slate-800 bg-slate-950/70 p-4">
                <div className="flex items-center gap-2">
                  <h3 className="font-medium">{fix.title ?? "Historical fix"}</h3>
                  {fix.verified && <Badge>Verified</Badge>}
                </div>
                <p className="mt-2 text-sm text-slate-400">{fix.description ?? fix.resolution ?? "No description recorded."}</p>
                <div className="mt-3 text-xs text-slate-600">{prettyDate(fix.created_at)} {fix.incident_id ? `· ${fix.incident_id}` : ""}</div>
              </article>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
