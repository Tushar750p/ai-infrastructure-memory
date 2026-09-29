"use client";

import { useEffect, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type GraphNode = {
  id: number;
  type: string;
  resource_id: string;
  name?: string;
  region?: string;
  status: string;
};

type GraphEdge = {
  source: number;
  target: number;
  type: string;
};

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
  const [awsAccountId, setAwsAccountId] = useState("");
  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState("");
  const [inventorySyncing, setInventorySyncing] = useState(false);
  const [inventoryMessage, setInventoryMessage] = useState("");
  const [graphNodes, setGraphNodes] = useState<GraphNode[]>([]);
  const [graphEdges, setGraphEdges] = useState<GraphEdge[]>([]);
  const [graphLoading, setGraphLoading] = useState(false);
  const [selectedNodeId, setSelectedNodeId] = useState<number | null>(null);
  const [correlation, setCorrelation] = useState<any>(null);
  const [correlationLoading, setCorrelationLoading] = useState(false);
  const [rca, setRca] = useState<any>(null);
  const [rcaLoading, setRcaLoading] = useState(false);
  const [fixMemory, setFixMemory] = useState<any>(null);
  const [fixMemoryLoading, setFixMemoryLoading] = useState(false);
  const [similarFixes, setSimilarFixes] = useState<any>(null);
  const [similarFixesLoading, setSimilarFixesLoading] = useState(false);

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
    if (organizationId) {
      loadEvents();
      loadGraph();
    }
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
      setAwsAccountId(String(data.account_id));
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

  async function syncCloudTrail() {
    if (!awsAccountId) return;
    setSyncing(true);
    setSyncMessage("");
    setError("");
    try {
      const response = await fetch(API_BASE + "/api/aws/accounts/" + awsAccountId + "/cloudtrail/sync", { method: "POST" });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "CloudTrail sync failed");
      setSyncMessage("CloudTrail sync complete. " + data.events_inserted + " new event(s) added.");
      await loadEvents();
    } catch (err) {
      setError(err instanceof Error ? err.message : "CloudTrail sync failed");
    } finally {
      setSyncing(false);
    }
  }



  async function loadGraph() {
    if (!organizationId) return;
    setGraphLoading(true);
    try {
      const response = await fetch(API_BASE + "/api/organizations/" + organizationId + "/graph", { cache: "no-store" });
      if (!response.ok) throw new Error("Graph API returned " + response.status);
      const data = await response.json();
      setGraphNodes(data.nodes || []);
      setGraphEdges(data.edges || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load infrastructure graph");
    } finally {
      setGraphLoading(false);
    }
  }




  async function loadFixMemory(resourceId: number) {
    if (!organizationId) return;
    setFixMemoryLoading(true);
    setFixMemory(null);
    setSimilarFixes(null);
    loadSimilarFixesForResource(resourceId);
    try {
      const response = await fetch(
        API_BASE + "/api/organizations/" + organizationId + "/resources/" + resourceId + "/fix-memory?limit=10",
        { cache: "no-store" },
      );
      if (!response.ok) throw new Error("Fix memory API returned " + response.status);
      setFixMemory(await response.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load fix memory");
    } finally {
      setFixMemoryLoading(false);
    }
  }



  async function loadSimilarFixesForResource(resourceId: number) {
    if (!organizationId) return;
    setSimilarFixesLoading(true);
    try {
      const response = await fetch(
        API_BASE + "/api/organizations/" + organizationId + "/resources/" + resourceId + "/similar-fixes?limit=5",
        { cache: "no-store" },
      );
      if (!response.ok) throw new Error("Resource similar fixes API returned " + response.status);
      setSimilarFixes(await response.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load recommended fixes");
    } finally {
      setSimilarFixesLoading(false);
    }
  }

  async function loadSimilarFixes(incidentId: number) {
    if (!organizationId) return;
    setSimilarFixesLoading(true);
    try {
      const response = await fetch(
        API_BASE + "/api/organizations/" + organizationId + "/incidents/" + incidentId + "/similar-fixes?limit=5",
        { cache: "no-store" },
      );
      if (!response.ok) throw new Error("Similar fixes API returned " + response.status);
      setSimilarFixes(await response.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load similar fixes");
    } finally {
      setSimilarFixesLoading(false);
    }
  }

  async function loadRca(resourceId: number) {
    if (!organizationId) return;
    setRcaLoading(true);
    setRca(null);
    loadFixMemory(resourceId);
    try {
      const response = await fetch(
        API_BASE + "/api/organizations/" + organizationId + "/resources/" + resourceId + "/rca?lookback_minutes=60&limit=25",
        { cache: "no-store" },
      );
      if (!response.ok) throw new Error("RCA API returned " + response.status);
      setRca(await response.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to generate RCA");
    } finally {
      setRcaLoading(false);
    }
  }

  async function loadCorrelation(resourceId: number) {
    if (!organizationId) return;
    setSelectedNodeId(resourceId);
    setCorrelationLoading(true);
    loadRca(resourceId);
    setCorrelation(null);
    try {
      const response = await fetch(
        API_BASE + "/api/organizations/" + organizationId + "/resources/" + resourceId + "/correlation?lookback_minutes=60&limit=25",
        { cache: "no-store" },
      );
      if (!response.ok) throw new Error("Correlation API returned " + response.status);
      setCorrelation(await response.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to analyze resource changes");
    } finally {
      setCorrelationLoading(false);
    }
  }

  async function syncInventory() {
    if (!awsAccountId) return;
    setInventorySyncing(true);
    setInventoryMessage("");
    setError("");
    try {
      const response = await fetch(API_BASE + "/api/aws/accounts/" + awsAccountId + "/inventory/sync", { method: "POST" });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Inventory sync failed");
      setInventoryMessage("AWS inventory sync complete. " + data.resources_discovered + " resource(s) scanned.");
      await loadGraph();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Inventory sync failed");
    } finally {
      setInventorySyncing(false);
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
          {awsAccountId && (
            <>
              <button onClick={syncCloudTrail} disabled={syncing} style={{ marginTop: 8, marginLeft: 8, background: "#7c3aed", border: 0, borderRadius: 8, padding: "11px 18px", color: "#fff", fontWeight: 700, cursor: "pointer", opacity: syncing ? 0.6 : 1 }}>
                {syncing ? "Syncing CloudTrail..." : "Sync CloudTrail"}
              </button>
              <button onClick={syncInventory} disabled={inventorySyncing} style={{ marginTop: 8, marginLeft: 8, background: "#0891b2", border: 0, borderRadius: 8, padding: "11px 18px", color: "#fff", fontWeight: 700, cursor: "pointer", opacity: inventorySyncing ? 0.6 : 1 }}>
                {inventorySyncing ? "Discovering AWS..." : "Sync Infrastructure"}
              </button>
            </>
          )}
          {syncMessage && <p style={{ color: "#a78bfa" }}>{syncMessage}</p>}
          {inventoryMessage && <p style={{ color: "#67e8f9" }}>{inventoryMessage}</p>}
        </section>

        <section style={{ marginTop: 32, display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
          <Metric title="Events in Memory" value={events.length.toString()} />
          <Metric title="Latest Source" value={events[0]?.source || "—"} />
          <Metric title="Latest Region" value={events[0]?.region || "—"} />
        </section>


        <section style={{ marginTop: 28, background: "#0b1728", border: "1px solid #1e293b", borderRadius: 14, padding: 22 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
            <div>
              <h2 style={{ margin: 0 }}>Infrastructure Topology</h2>
              <p style={{ color: "#64748b", marginBottom: 0 }}>Interactive map of the resources AIME discovered in AWS.</p>
            </div>
            <button onClick={loadGraph} disabled={graphLoading || !organizationId} style={{ background: "#334155", border: 0, borderRadius: 8, padding: "9px 14px", color: "#fff", fontWeight: 700, cursor: "pointer" }}>
              {graphLoading ? "Loading..." : "Refresh Topology"}
            </button>
          </div>
          {!organizationId && <p style={{ color: "#94a3b8" }}>Connect AWS or enter an organization ID to view the topology.</p>}
          {organizationId && graphNodes.length === 0 && !graphLoading && <p style={{ color: "#94a3b8" }}>No resources discovered yet. Run Sync Infrastructure.</p>}
          {graphNodes.length > 0 && (
            <TopologyCanvas
              nodes={graphNodes}
              edges={graphEdges}
              selectedNodeId={selectedNodeId}
              onSelect={loadCorrelation}
            />
          )}

          {correlationLoading && <p style={{ marginTop: 14, color: "#38bdf8" }}>Analyzing recent infrastructure changes...</p>}



          {similarFixesLoading && <p style={{ marginTop: 12, color: "#fbbf24" }}>Finding similar verified fixes...</p>}
          {similarFixes?.fixes?.length > 0 && (
            <div style={{ marginTop: 12, background: "#111827", border: "1px solid #334155", borderRadius: 10, padding: 16 }}>
              <strong>Recommended From SRE Memory</strong>
              {similarFixes.fixes.map((fix: any) => (
                <div key={fix.fix_id} style={{ marginTop: 10, padding: 10, borderRadius: 8, background: "#172033" }}>
                  <strong>{fix.title}</strong>
                  <div style={{ color: "#cbd5e1", fontSize: 12, marginTop: 4 }}>{fix.resolution}</div>
                  <div style={{ color: "#fbbf24", fontSize: 10, marginTop: 4 }}>
                    Match {Math.round(fix.similarity_score * 100)}% · {fix.matched_resource_type || "related resource"}
                  </div>
                </div>
              ))}
              <div style={{ color: "#64748b", fontSize: 10, marginTop: 8 }}>Stored commands are recommendations only; AIME never executes them automatically.</div>
            </div>
          )}
          {fixMemoryLoading && <p style={{ marginTop: 12, color: "#4ade80" }}>Searching previous fixes...</p>}
          {fixMemory && (
            <div style={{ marginTop: 12, background: "#081321", border: "1px solid #1e293b", borderRadius: 10, padding: 16 }}>
              <strong>What Fixed This Before?</strong>
              {fixMemory.count === 0 && <div style={{ color: "#64748b", fontSize: 12, marginTop: 7 }}>No previous verified fix is stored for this resource.</div>}
              {fixMemory.fixes?.map((fix: any) => (
                <div key={fix.id} style={{ marginTop: 10, padding: 10, borderRadius: 8, background: "#102033" }}>
                  <strong>{fix.title}</strong>
                  <div style={{ color: "#cbd5e1", fontSize: 12, marginTop: 4 }}>{fix.resolution}</div>
                  {fix.outcome && <div style={{ color: "#4ade80", fontSize: 11, marginTop: 4 }}>Outcome: {fix.outcome}</div>}
                  {fix.commands?.length > 0 && <div style={{ color: "#94a3b8", fontSize: 11, marginTop: 4 }}>Commands: {fix.commands.join(" · ")}</div>}
                  <div style={{ color: "#64748b", fontSize: 10, marginTop: 4 }}>{fix.verified ? "Verified fix" : "Recorded fix"} · {new Date(fix.created_at).toLocaleString()}</div>
                </div>
              ))}
            </div>
          )}
          {rcaLoading && <p style={{ marginTop: 12, color: "#c084fc" }}>Building evidence-based RCA...</p>}
          {rca && (
            <div style={{ marginTop: 12, background: "#081321", border: "1px solid #1e293b", borderRadius: 10, padding: 16 }}>
              <strong>Root Cause Analysis</strong>
              <div style={{ marginTop: 7, color: "#e2e8f0" }}>{rca.root_cause}</div>
              <div style={{ marginTop: 7, color: "#64748b", fontSize: 12 }}>Confidence: {rca.confidence} · Evidence: {rca.evidence?.length || 0}</div>
            </div>
          )}
          {correlation && (
            <div style={{ marginTop: 14, background: "#081321", border: "1px solid #1e293b", borderRadius: 10, padding: 16 }}>
              <strong>Change Correlation</strong>
              <div style={{ color: "#94a3b8", fontSize: 12, marginTop: 5 }}>{correlation.analysis}</div>
              {correlation.correlated_changes?.map((change: EventItem) => (
                <div key={change.id} style={{ marginTop: 10, padding: 10, borderRadius: 8, background: "#102033" }}>
                  <strong>{change.event_name}</strong>
                  <span style={{ color: "#64748b", marginLeft: 10, fontSize: 11 }}>{new Date(change.event_time).toLocaleString()}</span>
                  <div style={{ color: "#94a3b8", fontSize: 12, marginTop: 4 }}>{change.summary || change.resource_id || "Infrastructure change"}</div>
                </div>
              ))}
            </div>
          )}
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


function TopologyCanvas({
  nodes,
  edges,
  selectedNodeId,
  onSelect,
}: {
  nodes: GraphNode[];
  edges: GraphEdge[];
  selectedNodeId: number | null;
  onSelect: (id: number | null) => void;
}) {
  const width = 1080;
  const height = Math.max(430, Math.ceil(nodes.length / 4) * 150);
  const positions = new Map<number, { x: number; y: number }>();
  const order = ["ec2.vpc", "ec2.subnet", "ec2.instance", "rds.db_instance", "elasticache.replication_group", "ec2.security_group"];
  const sorted = [...nodes].sort((a, b) => {
    const ai = order.indexOf(a.type);
    const bi = order.indexOf(b.type);
    return (ai < 0 ? 99 : ai) - (bi < 0 ? 99 : bi);
  });

  sorted.forEach((node, index) => {
    const col = index % 4;
    const row = Math.floor(index / 4);
    positions.set(node.id, { x: 135 + col * 265, y: 70 + row * 145 });
  });

  const nodeColor = (type: string) => {
    if (type.includes("vpc")) return "#2563eb";
    if (type.includes("subnet")) return "#0891b2";
    if (type.includes("instance")) return "#16a34a";
    if (type.includes("rds")) return "#9333ea";
    if (type.includes("elasticache")) return "#ea580c";
    return "#475569";
  };

  return (
    <div style={{ marginTop: 18, overflow: "auto", background: "#050d17", border: "1px solid #1e293b", borderRadius: 12 }}>
      <svg viewBox={`0 0 ${width} ${height}`} width="100%" style={{ minWidth: 850, display: "block" }}>
        <defs>
          <marker id="aime-arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto">
            <path d="M0,0 L0,6 L7,3 z" fill="#64748b" />
          </marker>
        </defs>
        {edges.map((edge, index) => {
          const source = positions.get(edge.source);
          const target = positions.get(edge.target);
          if (!source || !target) return null;
          const active = selectedNodeId === edge.source || selectedNodeId === edge.target;
          return <g key={index}>
            <line x1={source.x} y1={source.y} x2={target.x} y2={target.y} stroke={active ? "#38bdf8" : "#334155"} strokeWidth={active ? 3 : 1.5} markerEnd="url(#aime-arrow)" />
            <text x={(source.x + target.x) / 2} y={(source.y + target.y) / 2 - 6} fill="#64748b" fontSize="9" textAnchor="middle">{edge.type}</text>
          </g>;
        })}
        {sorted.map((node) => {
          const pos = positions.get(node.id)!;
          const selected = selectedNodeId === node.id;
          return <g key={node.id} transform={`translate(${pos.x - 105},${pos.y - 35})`} onClick={() => onSelect(node.id)} style={{ cursor: "pointer" }}>
            <rect width="210" height="70" rx="10" fill="#0f1d30" stroke={selected ? "#38bdf8" : nodeColor(node.type)} strokeWidth={selected ? 3 : 1.5} />
            <circle cx="18" cy="20" r="6" fill={nodeColor(node.type)} />
            <text x="32" y="23" fill="#e2e8f0" fontSize="11" fontWeight="700">{node.type}</text>
            <text x="14" y="43" fill="#cbd5e1" fontSize="10">{(node.name || node.resource_id).slice(0, 30)}</text>
            <text x="14" y="58" fill="#64748b" fontSize="9">{node.status} · {node.region || "—"}</text>
          </g>;
        })}
      </svg>
      {selectedNodeId && (() => {
        const node = nodes.find((item) => item.id === selectedNodeId);
        if (!node) return null;
        const connected = edges.filter((edge) => edge.source === node.id || edge.target === node.id).length;
        return <div style={{ padding: 14, borderTop: "1px solid #1e293b", background: "#081321" }}>
          <strong>{node.name || node.resource_id}</strong>
          <div style={{ color: "#64748b", fontSize: 12, marginTop: 5 }}>{node.type} · {node.resource_id} · {node.status} · {connected} relationship(s)</div>
        </div>;
      })()}
    </div>
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
