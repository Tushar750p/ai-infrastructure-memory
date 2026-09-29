"use client";

import Link from "next/link";
import { useState } from "react";

const steps = [
  { title: "What changed?", eyebrow: "CHANGE INTELLIGENCE", headline: "A production deployment happened 11 minutes before the incident.", body: "AIME correlated the application deployment with a configuration change on the checkout service and the affected EC2 workload.", evidence: ["Deployment checkout-api v2.8.4", "Security-group/config update", "Affected: checkout-api / EC2"] },
  { title: "Why did it break?", eyebrow: "RCA", headline: "The change increased request latency under production load.", body: "Demo analysis connects timing, service telemetry and infrastructure change into one evidence chain. This is simulated buyer-demo data, not a live AWS environment.", evidence: ["Latency +184%", "Error rate +12.6%", "Correlation window: 11 min"] },
  { title: "Have we seen it before?", eyebrow: "INCIDENT MEMORY", headline: "A similar checkout latency incident exists in institutional memory.", body: "AIME found a previous incident with the same service pattern and a verified remediation recorded by the SRE team.", evidence: ["Similarity: 91%", "Previous incident: INC-1842", "Verified fix available"] },
  { title: "What fixed it before?", eyebrow: "VERIFIED FIX MEMORY", headline: "The previous fix reduced latency and cleared the alert.", body: "The stored remediation is presented with its evidence so an engineer can validate it before applying anything in production.", evidence: ["Rollback configuration", "Restart affected workload", "Post-fix latency normalized"] },
];

export default function DemoExperience() {
  const [active, setActive] = useState(0);
  const step = steps[active];

  return (
    <main style={{ minHeight: "100vh", background: "#050b14", color: "#e5edf7", fontFamily: "Arial, sans-serif" }}>
      <div style={{ maxWidth: 1180, margin: "0 auto", padding: "24px 24px 70px" }}>
        <nav style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <Link href="/demo" style={{ color: "#94a3b8", textDecoration: "none", fontSize: 14 }}>← AIME Overview</Link>
          <Link href="/" style={{ color: "#38bdf8", textDecoration: "none", fontWeight: 800, fontSize: 14 }}>Open Console →</Link>
        </nav>

        <header style={{ padding: "58px 0 30px" }}>
          <div style={{ color: "#38bdf8", fontSize: 12, fontWeight: 800, letterSpacing: ".14em" }}>INTERACTIVE BUYER DEMO · SIMULATED ENVIRONMENT</div>
          <h1 style={{ fontSize: "clamp(38px,6vw,68px)", lineHeight: 1, letterSpacing: "-.05em", margin: "14px 0 16px", maxWidth: 900 }}>From infrastructure change to verified fix.</h1>
          <p style={{ color: "#94a3b8", fontSize: 18, lineHeight: 1.55, maxWidth: 780, margin: 0 }}>Explore a simulated production incident and see how AIME turns scattered operational signals into persistent SRE memory.</p>
        </header>

        <section style={{ background: "#0b1422", border: "1px solid #26364d", borderRadius: 18, padding: 22 }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 8 }}>
            {steps.map((item, i) => (
              <button key={item.title} onClick={() => setActive(i)} style={{ textAlign: "left", border: i === active ? "1px solid #38bdf8" : "1px solid #1e293b", background: i === active ? "#0c2030" : "#08111e", color: "#e2e8f0", borderRadius: 10, padding: 15, cursor: "pointer" }}>
                <div style={{ color: "#38bdf8", fontSize: 11, fontWeight: 800 }}>0{i + 1}</div>
                <div style={{ marginTop: 7, fontWeight: 800 }}>{item.title}</div>
              </button>
            ))}
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1.25fr .75fr", gap: 18, marginTop: 18 }}>
            <article style={{ background: "#07101c", border: "1px solid #1e293b", borderRadius: 14, padding: 26 }}>
              <div style={{ color: "#64748b", fontSize: 11, fontWeight: 800, letterSpacing: ".12em" }}>{step.eyebrow}</div>
              <h2 style={{ fontSize: 29, lineHeight: 1.15, margin: "12px 0" }}>{step.headline}</h2>
              <p style={{ color: "#94a3b8", lineHeight: 1.65, fontSize: 16 }}>{step.body}</p>
              <div style={{ display: "grid", gap: 9, marginTop: 22 }}>
                {step.evidence.map((e) => <div key={e} style={{ padding: "12px 14px", background: "#0b1725", border: "1px solid #1e293b", borderRadius: 9 }}><span style={{ color: "#4ade80", marginRight: 8 }}>●</span>{e}</div>)}
              </div>
            </article>

            <aside style={{ background: "#07101c", border: "1px solid #1e293b", borderRadius: 14, padding: 22 }}>
              <div style={{ color: "#64748b", fontSize: 11, fontWeight: 800, letterSpacing: ".12em" }}>INCIDENT SNAPSHOT</div>
              <div style={{ marginTop: 18, fontSize: 22, fontWeight: 800 }}>INC-2417</div>
              <div style={{ color: "#f59e0b", fontSize: 13, fontWeight: 800, marginTop: 6 }}>SEV-2 · checkout-api</div>
              <div style={{ marginTop: 22, display: "grid", gap: 12 }}>
                {[["Latency", "+184%"], ["Errors", "+12.6%"], ["Change correlation", "0.94"], ["Fix confidence", "High"]].map(([k,v]) => <div key={k} style={{ display: "flex", justifyContent: "space-between", gap: 10, borderBottom: "1px solid #162235", paddingBottom: 10 }}><span style={{ color: "#94a3b8" }}>{k}</span><strong>{v}</strong></div>)}
              </div>
            </aside>
          </div>

          <div style={{ marginTop: 18, background: "#07101c", border: "1px solid #1e293b", borderRadius: 14, padding: 20 }}>
            <div style={{ color: "#64748b", fontSize: 11, fontWeight: 800, letterSpacing: ".12em" }}>INFRASTRUCTURE GRAPH · DEMO</div>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8, flexWrap: "wrap", padding: "28px 10px 8px" }}>
              {["ALB", "checkout-api", "EC2", "RDS", "Redis"].map((node, i) => <div key={node} style={{ display: "flex", alignItems: "center", gap: 8 }}><div style={{ padding: "12px 16px", borderRadius: 10, background: node === "checkout-api" ? "#0c2030" : "#0b1725", border: node === "checkout-api" ? "1px solid #38bdf8" : "1px solid #26364d", fontWeight: 800 }}>{node}</div>{i < 4 && <span style={{ color: "#475569" }}>→</span>}</div>)}
            </div>
          </div>
        </section>

        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, marginTop: 18 }}>
          <button onClick={() => setActive(Math.max(0, active - 1))} disabled={active === 0} style={{ padding: "13px 18px", borderRadius: 9, border: "1px solid #334155", background: "#08111e", color: active === 0 ? "#475569" : "#e2e8f0" }}>← Previous</button>
          <button onClick={() => setActive(Math.min(steps.length - 1, active + 1))} disabled={active === steps.length - 1} style={{ padding: "13px 18px", borderRadius: 9, border: "1px solid #38bdf8", background: "#38bdf8", color: "#03111d", fontWeight: 800 }}>Next insight →</button>
        </div>

        <section style={{ marginTop: 34, display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(210px,1fr))", gap: 12 }}>
          {[["01", "Connect", "Connect AWS or your infrastructure data."], ["02", "Correlate", "AIME connects changes, incidents and telemetry."], ["03", "Remember", "Verified fixes become reusable operational memory."]].map(([n,t,d]) => (
            <div key={n} style={{ background: "#0b1422", border: "1px solid #1e293b", borderRadius: 12, padding: 18 }}>
              <div style={{ color: "#38bdf8", fontWeight: 800 }}>{n}</div><strong style={{ display: "block", marginTop: 7 }}>{t}</strong><span style={{ display: "block", color: "#94a3b8", marginTop: 6, lineHeight: 1.45, fontSize: 14 }}>{d}</span>
            </div>
          ))}
        </section>

        <section style={{ marginTop: 48, textAlign: "center", padding: "40px 20px", borderTop: "1px solid #1e293b" }}>
          <div style={{ color: "#38bdf8", fontSize: 11, fontWeight: 800, letterSpacing: ".12em" }}>NEXT STEP</div>
          <h2 style={{ fontSize: 30, margin: "10px 0" }}>See what AIME can remember about your environment.</h2>
          <p style={{ color: "#94a3b8", margin: "10px auto 22px", maxWidth: 650 }}>The demo is simulated. The console connects to your real environment when you are ready for a technical evaluation or POC.</p>
          <Link href="/" style={{ display: "inline-block", background: "#38bdf8", color: "#03111d", padding: "14px 24px", borderRadius: 10, textDecoration: "none", fontWeight: 800 }}>Launch AIME Console →</Link>
        </section>
      </div>
    </main>
  );
}
