"use client";

import { useMemo, useState, type FormEvent, type MouseEvent } from "react";

import { intelligenceFor } from "@/lib/demand";
import type { DashboardData, Incident, Resource } from "@/lib/types";

function distance(left: Incident, right: Resource) {
  const radians = Math.PI / 180;
  const latitudeDelta = (right.latitude - left.latitude) * radians;
  const longitudeDelta = (right.longitude - left.longitude) * radians;
  const value = Math.sin(latitudeDelta / 2) ** 2
    + Math.cos(left.latitude * radians) * Math.cos(right.latitude * radians)
    * Math.sin(longitudeDelta / 2) ** 2;
  return 6371 * 2 * Math.atan2(Math.sqrt(value), Math.sqrt(1 - value));
}

function fit(incident: Incident, resource: Resource) {
  const needs: Record<string, string[]> = {
    flood: ["swift-water", "medical", "water", "shelter"],
    storm: ["medical", "shelter", "meals", "reconnaissance"],
    wildfire: ["medical", "evacuation", "water", "shelter"],
    earthquake: ["structural", "medical", "cots", "water"],
  };
  return resource.capabilities.filter((capability) => needs[incident.kind]?.includes(capability)).length;
}

function project(latitude: number, longitude: number) {
  return {
    left: `${Math.max(1, Math.min(99, ((longitude + 180) / 360) * 100))}%`,
    top: `${Math.max(2, Math.min(98, ((90 - latitude) / 180) * 100))}%`,
  };
}

export function OperationsBoard({ data }: { data: DashboardData }) {
  const [incidentId, setIncidentId] = useState(data.incidents[0]?.id ?? "");
  const [staged, setStaged] = useState<string[]>([]);
  const [revision, setRevision] = useState(1);
  const [customTarget, setCustomTarget] = useState<{ latitude: number; longitude: number } | null>(null);
  const [latitudeInput, setLatitudeInput] = useState("0");
  const [longitudeInput, setLongitudeInput] = useState("0");
  const selectedIncident = data.incidents.find((item) => item.id === incidentId) ?? data.incidents[0];
  const incident = useMemo(() => customTarget && selectedIncident ? {
      ...selectedIncident,
      id: "custom-global-target",
      title: `Custom target · ${customTarget.latitude.toFixed(2)}°, ${customTarget.longitude.toFixed(2)}°`,
      latitude: customTarget.latitude,
      longitude: customTarget.longitude,
    } : selectedIncident, [customTarget, selectedIncident]);
  const recommendations = useMemo(() => {
    if (!incident) return [];
    const demand = intelligenceFor(incident, data.resources);
    const gaps = new Map((demand.shortages ?? []).map((item) => [item.category, item]));
    return data.resources
      .filter((resource) => resource.available > 0 && !staged.includes(resource.id))
      .map((resource) => {
        const gap = resource.demandCategory ? gaps.get(resource.demandCategory) : undefined;
        const gapRatio = gap?.shortfall == null ? 0 : gap.shortfall / Math.max(1, gap.quantity);
        return { resource, distance: distance(incident, resource), fit: fit(incident, resource), gap, gapRatio };
      })
      .sort((left, right) => right.gapRatio - left.gapRatio || right.fit - left.fit || left.distance - right.distance)
      .slice(0, 4);
  }, [data.resources, incident, staged]);
  const immediatePlan = useMemo(() => incident ? intelligenceFor(incident, data.resources) : null, [data.resources, incident]);

  const stage = (resourceId: string) => {
    setStaged((current) => [...current, resourceId]);
    setRevision((current) => current + 1);
  };

  const setGlobalTarget = (latitude: number, longitude: number) => {
    const target = {
      latitude: Math.max(-90, Math.min(90, latitude)),
      longitude: Math.max(-180, Math.min(180, longitude)),
    };
    setCustomTarget(target);
    setLatitudeInput(target.latitude.toFixed(3));
    setLongitudeInput(target.longitude.toFixed(3));
    setRevision((current) => current + 1);
  };

  const chooseMapPoint = (event: MouseEvent<HTMLDivElement>) => {
    const bounds = event.currentTarget.getBoundingClientRect();
    const longitude = ((event.clientX - bounds.left) / bounds.width) * 360 - 180;
    const latitude = 90 - ((event.clientY - bounds.top) / bounds.height) * 180;
    setGlobalTarget(latitude, longitude);
  };

  const submitCoordinates = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setGlobalTarget(Number(latitudeInput), Number(longitudeInput));
  };

  if (!incident) return <main className="page-shell subpage">No active incidents.</main>;
  return <main className="page-shell subpage operations-page">
    <div className="operations-heading"><div><span className="eyebrow">Collaborative operations</span><h1>Common operating picture</h1><p>Coordinate incidents, infrastructure, shelters, people, and supplies from one continuously ranked workspace.</p></div><div className="revision-card"><span>Plan revision</span><strong>#{revision}</strong><button type="button" onClick={() => setRevision((current) => current + 1)}>Recalculate now</button></div></div>

    <div className="operations-grid">
      <section className="ops-map-card"><div className="ops-card-heading"><div><span className="eyebrow">Global live map</span><h2>{incident.title}</h2></div><span className="live-badge">{data.dataMode}</span></div><div className="ops-map" onClick={chooseMapPoint} role="application" aria-label="Global operations map. Click anywhere to create a staging target.">
        <svg viewBox="0 0 1000 500" role="img" aria-label="Simplified world operations map">
          <g className="world-grid"><path d="M0 125h1000M0 250h1000M0 375h1000M250 0v500M500 0v500M750 0v500" /></g>
          <g className="world-land"><path d="M42 92 96 49l108 5 77 42 13 61-50 40-43 72-68-22-32-68-54-31Z" /><path d="m259 238 80 18 51 55-19 83-44 81-37-68-9-82-34-47Z" /><path d="m449 111 47-35 62 13 35 48-40 28-58-13Z" /><path d="m473 174 91-14 70 63-21 113-70 70-46-95-51-74Z" /><path d="m570 88 103-48 142 20 130 67-30 72-101 19-70-39-78 49-83-39 25-56Z" /><path d="m792 344 79-35 77 44-28 75-94 8-48-48Z" /><path d="m26 455 110 11 154-3 161 11 166-8 185 9 166-14" /></g>
        </svg>
        {data.resources.map((resource) => <span className="asset-pin" style={project(resource.latitude, resource.longitude)} key={resource.id} title={resource.name}>R</span>)}
        {customTarget ? <span className="target-pin" style={project(customTarget.latitude, customTarget.longitude)} aria-label="Custom staging target">+</span> : null}
        {data.incidents.map((item) => <button type="button" className={`event-pin ${item.severity} ${!customTarget && item.id === incident.id ? "selected" : ""}`} style={project(item.latitude, item.longitude)} key={item.id} onClick={(event) => { event.stopPropagation(); setCustomTarget(null); setIncidentId(item.id); setRevision((current) => current + 1); }} aria-label={`Plan for ${item.title}`}>{Math.round(item.riskScore)}</button>)}
      </div><div className="map-caption"><span>● Incident risk index</span><span>R Response asset</span><span>+ Custom target</span><span>Click anywhere worldwide</span></div><form className="coordinate-picker" onSubmit={submitCoordinates}><label>Latitude<input type="number" min="-90" max="90" step="0.001" value={latitudeInput} onChange={(event) => setLatitudeInput(event.target.value)} /></label><label>Longitude<input type="number" min="-180" max="180" step="0.001" value={longitudeInput} onChange={(event) => setLongitudeInput(event.target.value)} /></label><button type="submit">Set global target</button></form></section>

      <aside className="staging-card"><div className="ops-card-heading"><div><span className="eyebrow">Recommended staging</span><h2>Next best moves</h2></div><span className="live-badge">gap-ranked</span></div><div className="recommendation-list">{recommendations.map(({ resource, distance: distanceKm, fit: match, gap }) => <article key={resource.id}><div><span>{gap?.urgency ?? resource.kind} priority</span><strong>{resource.name}</strong><small>{resource.available.toLocaleString()} {resource.unit ?? "units"} · {Math.round(distanceKm)} km · {match} capability matches</small>{gap?.shortfall != null ? <em>{gap.shortfall.toLocaleString()} {gap.unit} estimated gap</em> : null}</div><button type="button" onClick={() => stage(resource.id)}>Stage</button></article>)}</div>{staged.length > 0 && <div className="staged-note">{staged.length} asset group{staged.length > 1 ? "s" : ""} staged. Remaining options reranked automatically.</div>}</aside>
    </div>

    <section className="ops-section"><div className="ops-card-heading"><div><span className="eyebrow">Six-hour demand gaps</span><h2>Immediate needs versus available inventory</h2></div><span className="transparency-label">modeled estimate</span></div><div className="gap-grid">{(immediatePlan?.shortages ?? []).map((item) => <article key={item.category}><span className={`gap-label ${item.urgency}`}>{item.urgency}</span><h3>{item.label}</h3><strong>{(item.shortfall ?? item.quantity).toLocaleString()}</strong><small>{item.unit} shortfall</small><div><i style={{ width: `${Math.round((item.coverage ?? 0) * 100)}%` }} /></div><p>{item.available?.toLocaleString() ?? "—"} available / {item.quantity.toLocaleString()} estimated</p></article>)}</div><p className="safety-note"><strong>Human confirmation required:</strong> CrisisMesh ranks staging options from modeled demand, inventory, capability fit, and distance. It never dispatches assets autonomously.</p></section>

    <section className="ops-section"><div className="ops-card-heading"><div><span className="eyebrow">Response capacity</span><h2>Shelters, volunteers, supplies, and teams</h2></div></div><div className="capacity-grid">{data.resources.map((resource) => <article key={resource.id}><span>{resource.kind}</span><strong>{resource.available.toLocaleString()}</strong><h3>{resource.name}</h3><p>{resource.capabilities.join(" · ")}</p><div><i style={{ width: `${Math.round(resource.available / resource.quantity * 100)}%` }} /></div><small>{Math.round(resource.available / resource.quantity * 100)}% available</small></article>)}</div></section>

    <section className="ops-section"><div className="ops-card-heading"><div><span className="eyebrow">Infrastructure status</span><h2>Critical systems</h2></div><span className="transparency-label">Status provenance shown</span></div><div className="infrastructure-grid">{data.infrastructure.map((system) => <article key={system.id}><span className={`infra-status ${system.status}`}>{system.status}</span><h3>{system.name}</h3><p>{system.detail}</p><small>{system.source} · {new Date(system.updatedAt).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", timeZone: "UTC" })} UTC</small></article>)}</div><p className="safety-note"><strong>Infrastructure transparency:</strong> demo or incident-derived statuses are explicitly labeled and are never presented as verified utility telemetry. Production adapters can replace them without changing the coordination workflow.</p></section>
  </main>;
}
