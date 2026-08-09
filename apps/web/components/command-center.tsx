"use client";

import { useEffect, useMemo, useState, useTransition } from "react";
import type { Allocation, DashboardData, Incident } from "@/lib/types";
import { CommandHeader } from "./command-header";
import { Icon } from "./icons";
import { IncidentList } from "./incident-list";
import { IncidentMap } from "./incident-map";
import { ResourcePanel } from "./resource-panel";

const kinds = ["all", "storm", "flood", "wildfire", "earthquake"];
const formatPopulation = (value: number) => value >= 1_000_000 ? `${(value / 1_000_000).toFixed(1)}m` : `${Math.round(value / 1000)}k`;
const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

export function CommandCenter({ initialData }: { initialData: DashboardData }) {
  const [incidents, setIncidents] = useState(initialData.incidents);
  const [selectedId, setSelectedId] = useState(initialData.incidents[0]?.id ?? "");
  const [kind, setKind] = useState("all");
  const [allocations, setAllocations] = useState<Allocation[]>([]);
  const [notice, setNotice] = useState(initialData.connected ? "Live data mesh synchronized" : "Embedded response scenario loaded");
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    if (!initialData.connected) return;
    const stream = new EventSource(`${apiUrl}/api/v1/stream`);
    stream.addEventListener("update", (message) => {
      try {
        const event = JSON.parse((message as MessageEvent<string>).data) as { type: string; data: Incident };
        if (event.type === "incident.updated") {
          setIncidents((current) => [event.data, ...current.filter((item) => item.id !== event.data.id)]);
          setNotice(`Signal updated · ${event.data.source}`);
        }
      } catch { setNotice("Live stream delivered an unreadable event"); }
    });
    stream.onerror = () => setNotice("Live stream reconnecting");
    return () => stream.close();
  }, [initialData.connected]);

  const filtered = useMemo(() => kind === "all" ? incidents : incidents.filter((item) => item.kind === kind), [incidents, kind]);
  const selected = incidents.find((item) => item.id === selectedId) ?? incidents[0];

  async function deployResources() {
    if (!selected) return;
    startTransition(async () => {
      if (!initialData.connected) {
        const simulated = initialData.resources.slice(0, 3).map((resource, index): Allocation => ({ id: `scenario-${index}`, incidentId: selected.id, resourceId: resource.id, units: Math.min(resource.available, 4 + index), etaSeconds: 2100 + index * 900, distanceKm: 82 + index * 74, suitability: 0.91 - index * 0.09, rationale: "Scenario-mode capability and proximity match.", status: "proposed", createdAt: new Date().toISOString() }));
        setAllocations(simulated); setNotice("Response package simulated · 3 assets matched"); return;
      }
      try {
        const response = await fetch(`${apiUrl}/api/v1/allocations`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ incidentId: selected.id }) });
        if (!response.ok) throw new Error(`allocation returned ${response.status}`);
        const body = await response.json() as { data: Allocation[] };
        setAllocations(body.data); setNotice(`Response package ready · ${body.data.length} assets matched`);
      } catch { setNotice("Allocation service unavailable"); }
    });
  }

  return (
    <main id="top" className="command-shell">
      <CommandHeader connected={initialData.connected} incidentCount={incidents.length} />
      <div className="status-strip"><Icon name="radio" /><span role="status" aria-live="polite">{notice}</span><i /><span>All times UTC</span><i /><span>Decision-support system · verify official guidance</span></div>
      <section className="metric-grid" aria-label="Operational summary">
        <Metric label="Active incidents" value={String(initialData.summary.activeIncidents).padStart(2, "0")} note={`${initialData.summary.criticalIncidents} critical`} tone="danger" />
        <Metric label="Population exposed" value={formatPopulation(initialData.summary.affectedPopulation)} note="modeled estimate" />
        <Metric label="Resources ready" value={String(initialData.summary.resourcesAvailable)} note={`${initialData.resources.length} asset groups`} tone="good" />
        <Metric label="Mean risk index" value={Math.round(initialData.summary.meanRiskScore).toString()} note="out of 100" />
      </section>
      <div className="filter-row"><span>Hazard layer</span>{kinds.map((item) => <button key={item} className={kind === item ? "active" : ""} onClick={() => setKind(item)}>{item}</button>)}<span className="filter-spacer" /><span className="last-sync"><i />{initialData.connected ? "STREAMING" : "DEMO DATA"}</span></div>
      <div className="operations-grid">
        <div className="primary-column"><IncidentMap incidents={filtered} resources={initialData.resources} selectedId={selected?.id ?? ""} onSelect={setSelectedId} /><IncidentList incidents={filtered} selectedId={selected?.id ?? ""} onSelect={setSelectedId} /></div>
        <aside className="intel-column">
          {selected && <section className="incident-detail">
            <div className="detail-top"><span className={`severity-badge ${selected.severity}`}>{selected.severity}</span><span>{selected.source}</span></div>
            <p className="eyebrow">INCIDENT {selected.id.toUpperCase()}</p><h1>{selected.title}</h1><p className="detail-description">{selected.description}</p>
            <div className="risk-block"><div><span>OPERATIONAL RISK</span><strong>{Math.round(selected.riskScore)}</strong></div><div className="risk-track"><i style={{ width: `${selected.riskScore}%` }} /></div><small>{Math.round(selected.confidence * 100)}% source confidence</small></div>
            <dl className="detail-facts"><div><dt>Population</dt><dd>{selected.affectedPopulation.toLocaleString("en-US")}</dd></div><div><dt>Coordinates</dt><dd>{selected.latitude.toFixed(2)}, {selected.longitude.toFixed(2)}</dd></div><div><dt>Regions</dt><dd>{selected.regions.length}</dd></div></dl>
            <button className="primary-button" onClick={deployResources} disabled={isPending}><Icon name="route" />{isPending ? "Calculating response…" : "Generate response package"}</button>
            <p className="decision-note"><Icon name="alert" />Recommendations require operator approval before dispatch.</p>
          </section>}
          <ResourcePanel resources={initialData.resources} allocations={allocations} />
          <section className="source-panel"><div className="section-heading"><div><span className="eyebrow">DATA MESH</span><h2>Source health</h2></div><Icon name="activity" /></div>{initialData.summary.sources.map((source) => <div className="source-row" key={source.name}><span><i className={source.status} />{source.name}</span><b>{source.lagSeconds}s</b></div>)}</section>
        </aside>
      </div>
      <footer><span>CRISIS<span>MESH</span> / OPEN RESPONSE INFRASTRUCTURE</span><span>NASA EONET · NOAA/NWS · USGS</span><span>v0.1.0</span></footer>
    </main>
  );
}

function Metric({ label, value, note, tone = "" }: { label: string; value: string; note: string; tone?: string }) {
  return <article className={`metric ${tone}`}><span>{label}</span><strong>{value}</strong><small>{note}</small></article>;
}
