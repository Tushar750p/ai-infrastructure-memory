"use client";

import Link from "next/link";

const capabilities = [
  ["Infrastructure Memory", "Remember AWS resources, changes, events and operational context."],
  ["Change Intelligence", "Connect infrastructure changes with incidents and service impact."],
  ["Incident Intelligence", "Build timelines, evidence and confidence around incidents."],
  ["Verified Fix Memory", "Reuse fixes that worked before instead of starting from zero."],
  ["Infrastructure Graph", "Understand relationships between cloud resources."],
  ["AI SRE Copilot", "Ask what changed, why it happened and what fixed it before."],
];

export default function DemoLanding() {
  return (
    <main style={{ minHeight: "100vh", background: "#050b14", color: "#e5edf7", fontFamily: "Arial, sans-serif" }}>
      <div style={{ maxWidth: 1180, margin: "0 auto", padding: "28px 24px 80px" }}>
        <nav style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ fontWeight: 800, fontSize: 22, letterSpacing: "-0.03em" }}>AIME</div>
          <div style={{ display: "flex", gap: 16, alignItems: "center", flexWrap: "wrap" }}>
            <Link href="/reports" style={{ color: "#cbd5e1", textDecoration: "none", fontSize: 14 }}>SRE Reports</Link>
            <Link href="/time-machine" style={{ color: "#cbd5e1", textDecoration: "none", fontSize: 14 }}>Time Machine</Link>
            <Link href="/" style={{ color: "#cbd5e1", textDecoration: "none", fontSize: 14 }}>Open Console →</Link>
          </div>
        </nav>

        <section style={{ padding: "100px 0 72px", maxWidth: 900 }}>
          <div style={{ color: "#38bdf8", fontWeight: 700, fontSize: 13, letterSpacing: "0.12em", textTransform: "uppercase" }}>
            AI Infrastructure Memory
          </div>
          <h1 style={{ fontSize: "clamp(44px, 7vw, 78px)", lineHeight: 0.98, margin: "18px 0 24px", letterSpacing: "-0.055em" }}>
            Your infrastructure should remember what happened.
          </h1>
          <p style={{ color: "#94a3b8", fontSize: 21, lineHeight: 1.55, maxWidth: 760, margin: 0 }}>
            AIME connects infrastructure changes, incidents, telemetry, RCA and verified fixes into a persistent operational memory for engineering teams.
          </p>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginTop: 34 }}>
            <Link href="/demo/experience" style={{ background: "#38bdf8", color: "#03111d", padding: "14px 22px", borderRadius: 10, textDecoration: "none", fontWeight: 800 }}>
              Experience AIME Demo →
            </Link>
            <Link href="/" style={{ border: "1px solid #334155", color: "#e2e8f0", padding: "14px 22px", borderRadius: 10, textDecoration: "none", fontWeight: 700 }}>
              Try AIME Console
            </Link>
            <Link href="/time-machine" style={{ border: "1px solid #334155", color: "#e2e8f0", padding: "14px 22px", borderRadius: 10, textDecoration: "none", fontWeight: 700 }}>
              Explore Time Machine
            </Link>
            <a href="#capabilities" style={{ border: "1px solid #334155", color: "#e2e8f0", padding: "14px 22px", borderRadius: 10, textDecoration: "none", fontWeight: 700 }}>
              Explore capabilities
            </a>
          </div>
        </section>

        <section id="capabilities" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(260px,1fr))", gap: 14 }}>
          {capabilities.map(([title, description]) => (
            <article key={title} style={{ background: "#0b1422", border: "1px solid #1e293b", borderRadius: 14, padding: 22 }}>
              <div style={{ color: "#38bdf8", fontSize: 12, fontWeight: 800, marginBottom: 12 }}>AIME</div>
              <h2 style={{ fontSize: 20, margin: "0 0 9px" }}>{title}</h2>
              <p style={{ color: "#94a3b8", lineHeight: 1.55, margin: 0 }}>{description}</p>
            </article>
          ))}
        </section>

        <section style={{ marginTop: 48, background: "linear-gradient(135deg,#0b1728,#101b31)", border: "1px solid #26364d", borderRadius: 18, padding: 30 }}>
          <div style={{ color: "#64748b", fontSize: 12, textTransform: "uppercase", letterSpacing: "0.12em", fontWeight: 800 }}>The SRE memory loop</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(150px,1fr))", gap: 10, marginTop: 20 }}>
            {["What changed?", "What broke?", "Why did it break?", "Have we seen it?", "What fixed it?"].map((item, i) => (
              <div key={item} style={{ padding: 18, borderRadius: 10, background: "#08111e", border: "1px solid #1e293b", color: "#dbeafe", fontWeight: 700 }}>
                <span style={{ color: "#38bdf8", marginRight: 8 }}>0{i + 1}</span>{item}
              </div>
            ))}
          </div>
        </section>

        <section style={{ textAlign: "center", padding: "78px 0 20px" }}>
          <h2 style={{ fontSize: 34, margin: 0 }}>See the memory loop in action.</h2>
          <p style={{ color: "#94a3b8", margin: "12px auto 24px", maxWidth: 600 }}>
            Walk through a simulated production incident: change → impact → RCA → previous incident → verified fix.
          </p>
          <Link href="/demo/experience" style={{ display: "inline-block", background: "#38bdf8", color: "#03111d", padding: "14px 24px", borderRadius: 10, textDecoration: "none", fontWeight: 800 }}>
            Start Interactive Demo →
          </Link>
        </section>

        <footer style={{ borderTop: "1px solid #1e293b", marginTop: 60, paddingTop: 20, color: "#64748b", fontSize: 12 }}>
          AIME — AI Infrastructure Memory · Built for cloud, platform and SRE teams.
        </footer>
      </div>
    </main>
  );
}
