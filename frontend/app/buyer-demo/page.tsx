"use client";

import { useMemo, useState } from "react";
import Link from "next/link";

const nav = [
  ["Dashboard","📊"],["Memory","🧠"],["Incidents","🚨"],["Topology","🕸️"],
  ["Time Machine","🕐"],["Reports","📑"],["Copilot","🤖"],["Security","🔐"]
];
const events = [
  ["09:42","Deployment","checkout-api","v2.8.4 deployed","High"],
  ["09:47","Config change","checkout-api","Security group rule updated","Medium"],
  ["09:53","Telemetry","checkout-api","Latency crossed 500ms","High"],
  ["09:54","Incident","INC-2417","Checkout latency incident opened","SEV-2"],
  ["10:08","Fix memory","checkout-api","Verified remediation identified","High"],
];

export default function BuyerDemoPage() {
  const [active,setActive]=useState("Dashboard");
  const [search,setSearch]=useState("");
  const [question,setQuestion]=useState("");
  const [answer,setAnswer]=useState("Ask AIME what changed, why it mattered, or what fixed it before.");
  const filtered=useMemo(()=>events.filter(e=>e.join(" ").toLowerCase().includes(search.toLowerCase())),[search]);
  const ask=()=>{
    const q=question.toLowerCase();
    if(q.includes("fix")||q.includes("before")) setAnswer("A previous checkout incident was resolved with a configuration rollback followed by a workload restart. AIME presents the verified evidence for engineer validation; it does not execute production changes automatically.");
    else if(q.includes("why")||q.includes("break")||q.includes("incident")) setAnswer("AIME correlates the 09:42 deployment and 09:47 configuration change with the 09:53 latency spike. Demo confidence is High and the correlation window is 11 minutes.");
    else setAnswer("AIME found the checkout-api deployment, configuration change, telemetry anomaly and previous incident memory. Try: What changed? Why did it break? What fixed it before?");
  };
  return <main className="buyer-shell">
    <aside className="buyer-side">
      <div className="buyer-logo">AI<span>ME</span></div>
      {nav.map(([name,icon])=><button key={name} className={"buyer-nav "+(active===name?"active":"")} onClick={()=>setActive(name)}><b>{icon}</b> <span>{name}</span></button>)}
      <div className="buyer-demo-label">BUYER DEMO<br/><span>SIMULATED ENVIRONMENT</span></div>
    </aside>
    <section className="buyer-main">
      <header className="buyer-top"><div>AIME Console / <strong>{active}</strong></div><div className="buyer-top-actions"><span className="buyer-pill green">Demo Online</span><Link href="/demo" className="buyer-btn">Overview</Link></div></header>
      <div className="buyer-content">
        {active==="Dashboard"&&<Dashboard setActive={setActive}/>}
        {active==="Memory"&&<Memory search={search} setSearch={setSearch} rows={filtered}/>}
        {active==="Incidents"&&<Incidents setActive={setActive}/>}
        {active==="Topology"&&<Topology/>}
        {active==="Time Machine"&&<TimeMachine/>}
        {active==="Reports"&&<Reports/>}
        {active==="Copilot"&&<Copilot question={question} setQuestion={setQuestion} answer={answer} ask={ask}/>}
        {active==="Security"&&<Security/>}
      </div>
    </section>
  </main>;
}

function Dashboard({setActive}:{setActive:(s:string)=>void}){return <><h1 className="buyer-h1">Infrastructure command center</h1><p className="buyer-muted">Persistent operational memory across your cloud environment.</p><div className="buyer-grid4 buyer-gap"><Stat l="Resources" v="24"/><Stat l="Events" v="1,284"/><Stat l="Incidents" v="7"/><Stat l="Verified fixes" v="18"/></div><div className="buyer-grid2 buyer-gap"><div className="buyer-card"><span className="buyer-pill amber">SEV-2 · OPEN</span><h2>INC-2417 · checkout-api latency</h2><p className="buyer-muted">Latency +184% · Errors +12.6% · Correlation 0.94</p><button className="buyer-btn primary" onClick={()=>setActive("Incidents")}>Investigate incident →</button></div><div className="buyer-card"><h3>SRE memory loop</h3><p className="buyer-muted">Change → impact → RCA → previous incident → verified fix</p><div className="buyer-pills">{["Change","Correlate","Remember","Reuse"].map(x=><span className="buyer-pill" key={x}>{x}</span>)}</div></div></div><div className="buyer-card buyer-gap"><h3>Latest infrastructure signals</h3><EventTable/></div></>}

function Stat({l,v}:{l:string;v:string}){return <div className="buyer-card"><div className="buyer-label">{l}</div><div className="buyer-metric">{v}</div><div className="buyer-muted small">Demo environment</div></div>}

function EventTable(){return <table className="buyer-table"><thead><tr><th>TIME</th><th>TYPE</th><th>RESOURCE</th><th>EVENT</th><th>IMPACT</th></tr></thead><tbody>{events.map(e=><tr key={e.join("-")}><td>{e[0]}</td><td>{e[1]}</td><td>{e[2]}</td><td>{e[3]}</td><td>{e[4]}</td></tr>)}</tbody></table>}

function Memory({search,setSearch,rows}:{search:string;setSearch:(s:string)=>void;rows:string[][]}){return <><h1 className="buyer-h1">Infrastructure Memory</h1><p className="buyer-muted">Searchable operational context across changes, incidents and fixes.</p><div className="buyer-search"><input className="buyer-input" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search changes, resources, incidents..."/><button className="buyer-btn primary">Remember</button></div><div className="buyer-card"><table className="buyer-table"><thead><tr><th>TIME</th><th>TYPE</th><th>RESOURCE</th><th>DETAIL</th><th>IMPACT</th></tr></thead><tbody>{rows.map(e=><tr key={e.join("-")}><td>{e[0]}</td><td>{e[1]}</td><td>{e[2]}</td><td>{e[3]}</td><td>{e[4]}</td></tr>)}</tbody></table></div></>}

function Incidents({setActive}:{setActive:(s:string)=>void}){return <><h1 className="buyer-h1">Incident Intelligence</h1><p className="buyer-muted">Evidence, timeline, RCA and previous fixes in one view.</p><div className="buyer-card buyer-gap"><span className="buyer-pill amber">SEV-2 · OPEN</span><h2>INC-2417 · checkout-api latency</h2><p className="buyer-muted">Latency +184% · Errors +12.6% · Change correlation 0.94 · Fix confidence High</p><div className="buyer-grid2"><div><h3>Evidence timeline</h3>{events.map(e=><div className="buyer-timeline" key={e.join("-")}><strong>{e[0]}</strong><span>{e[3]}</span><small>{e[1]} · {e[2]}</small></div>)}</div><div><h3>Root cause signal</h3><div className="buyer-highlight">Configuration change correlated with deployment</div><p className="buyer-muted">Timing, telemetry and infrastructure relationships form the evidence chain.</p><h3>Verified fix memory</h3><div className="buyer-card inner"><strong>Rollback checkout configuration</strong><p className="buyer-muted">Previously reduced latency and cleared the alert.</p><button className="buyer-btn" onClick={()=>setActive("Time Machine")}>View historical evidence →</button></div></div></div></div></>}

function Topology(){return <><h1 className="buyer-h1">Infrastructure Graph</h1><p className="buyer-muted">Relationships across the application path.</p><div className="buyer-card buyer-gap"><div className="buyer-graph">{[["ALB","healthy"],["checkout-api","degraded"],["EC2","healthy"],["RDS","healthy"],["Redis","healthy"]].map((x,i)=><div className="buyer-graph-item" key={x[0]}><div className="buyer-node"><strong>{x[0]}</strong><small>AWS resource</small><span className={"buyer-pill "+(x[1]==="degraded"?"amber":"green")}>{x[1]}</span></div>{i<4&&<span className="buyer-arrow">→</span>}</div>)}</div><div className="buyer-grid4"><Stat l="Resources" v="24"/><Stat l="Relationships" v="31"/><Stat l="Resource types" v="5"/><Stat l="Correlation" v="0.94"/></div></div></>}

function TimeMachine(){return <><h1 className="buyer-h1">Infrastructure Time Machine</h1><p className="buyer-muted">Reconstruct what happened before, during and after an incident.</p><div className="buyer-card buyer-gap">{[["09:42","checkout-api v2.8.4","Deployment"],["09:47","Security group rule changed","Configuration"],["09:53","Latency anomaly detected","Telemetry"],["09:54","INC-2417 opened","Incident"],["10:08","Verified remediation found","Memory"]].map(x=><div className="buyer-time-row" key={x[0]}><strong>{x[0]}</strong><span>{x[1]}</span><span className="buyer-pill">{x[2]}</span></div>)}<div className="buyer-note"><strong>Historical fix evidence</strong><p className="buyer-muted">Previous verified remediation: configuration rollback → workload restart → latency validation.</p></div></div></>}

function Reports(){return <><h1 className="buyer-h1">SRE Reports</h1><p className="buyer-muted">Operational report generated from the AIME demo memory model.</p><div className="buyer-grid4 buyer-gap"><Stat l="Events" v="1,284"/><Stat l="Incidents" v="7"/><Stat l="Open" v="2"/><Stat l="Verified fixes" v="18"/></div><div className="buyer-card buyer-gap"><h3>Incident summary</h3><p>checkout-api · SEV-2 · configuration change correlated with latency spike · verified remediation available.</p><button className="buyer-btn primary" onClick={()=>window.print()}>Print / Save PDF</button></div></>}

function Copilot({question,setQuestion,answer,ask}:{question:string;setQuestion:(s:string)=>void;answer:string;ask:()=>void}){return <><h1 className="buyer-h1">AI SRE Copilot</h1><p className="buyer-muted">Ask the infrastructure memory what changed, why it mattered and what worked before.</p><div className="buyer-card buyer-gap"><div className="buyer-answer"><span className="buyer-pill">AIME MEMORY</span><p>{answer}</p></div><div className="buyer-search"><input className="buyer-input" value={question} onChange={e=>setQuestion(e.target.value)} onKeyDown={e=>e.key==="Enter"&&ask()} placeholder="What fixed this before?"/><button className="buyer-btn primary" onClick={ask}>Ask AIME</button></div><div className="buyer-pills">{["What changed?","Why did it break?","What fixed it before?"].map(q=><button className="buyer-btn" key={q} onClick={()=>{setQuestion(q);setTimeout(ask,0)}}>{q}</button>)}</div></div></>}

function Security(){return <><h1 className="buyer-h1">Security & RBAC</h1><p className="buyer-muted">Enterprise controls shown in the buyer demo environment.</p><div className="buyer-grid2 buyer-gap"><div className="buyer-card"><h3>Organization</h3><p>AIME Demo Organization</p><span className="buyer-pill green">Protected</span><h3>Roles</h3><p className="buyer-muted">Owner · Admin · Viewer</p></div><div className="buyer-card"><h3>Audit activity</h3>{["Login verified","Incident memory viewed","Time Machine opened","Report generated"].map((x,i)=><div className="buyer-timeline" key={x}><strong>{x}</strong><small>Today · {10+i}:2{i}</small></div>)}</div></div></>}
