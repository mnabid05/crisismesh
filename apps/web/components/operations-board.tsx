"use client";

import { useMemo, useState } from "react";

import type { DashboardData, Incident, Resource } from "@/lib/types";

function distance(left: Incident, right: Resource) {
  const latitude = (left.latitude - right.latitude) * 111;
  const longitude = (left.longitude - right.longitude) * 88;
  return Math.sqrt(latitude * latitude + longitude * longitude);
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
    left: `${Math.max(4, Math.min(96, ((longitude + 130) / 65) * 100))}%`,
    top: `${Math.max(5, Math.min(93, ((50 - latitude) / 26) * 100))}%`,
  };
}

export function OperationsBoard({ data }: { data: DashboardData }) {
  const [incidentId, setIncidentId] = useState(data.incidents[0]?.id ?? "");
  const [staged, setStaged] = useState<string[]>([]);
  const [revision, setRevision] = useState(1);
  const incident = data.incidents.find((item) => item.id === incidentId) ?? data.incidents[0];
  const recommendations = useMemo(() => {
    if (!incident) return [];
    return data.resources
      .filter((resource) => resource.available > 0 && !staged.includes(resource.id))
      .map((resource) => ({ resource, distance: distance(incident, resource), fit: fit(incident, resource) }))
      .sort((left, right) => right.fit - left.fit || left.distance - right.distance)
      .slice(0, 4);
  }, [data.resources, incident, staged]);

  const stage = (resourceId: string) => {
    setStaged((current) => [...current, resourceId]);
    setRevision((current) => current + 1);
  };

  if (!incident) return <main className="page-shell subpage">No active incidents.</main>;
  return <main className="page-shell subpage operations-page">
    <div className="operations-heading"><div><span className="eyebrow">Collaborative operations</span><h1>Common operating picture</h1><p>Coordinate incidents, infrastructure, shelters, people, and supplies from one continuously ranked workspace.</p></div><div className="revision-card"><span>Plan revision</span><strong>#{revision}</strong><button type="button" onClick={() => setRevision((current) => current + 1)}>Recalculate now</button></div></div>

    <div className="operations-grid">
      <section className="ops-map-card"><div className="ops-card-heading"><div><span className="eyebrow">Live map</span><h2>{incident.title}</h2></div><span className="live-badge">{data.dataMode}</span></div><div className="ops-map">
        <svg viewBox="0 0 1000 600" role="img" aria-label="Simplified United States operations map"><path d="M85 88 173 64l70 31 95-10 90 21 87-2 66 27 92-10 83 36 76 5 78 55-12 64-58 47-22 63-54 10-43 73-43-2-11-79-39-22-30-71-78-34-63 28-90-2-56 27-57-61-68-11-48-59-41-5-27-83Z" /></svg>
        {data.resources.map((resource) => <span className="asset-pin" style={project(resource.latitude, resource.longitude)} key={resource.id} title={resource.name}>R</span>)}
        {data.incidents.map((item) => <button type="button" className={`event-pin ${item.severity} ${item.id === incident.id ? "selected" : ""}`} style={project(item.latitude, item.longitude)} key={item.id} onClick={() => { setIncidentId(item.id); setRevision((current) => current + 1); }} aria-label={`Plan for ${item.title}`}>{Math.round(item.riskScore)}</button>)}
      </div><div className="map-caption"><span>● Incident risk index</span><span>R Response asset</span><span>Select an incident to recalculate staging</span></div></section>

      <aside className="staging-card"><div className="ops-card-heading"><div><span className="eyebrow">Recommended staging</span><h2>Next best moves</h2></div><span className="live-badge">auto-ranked</span></div><div className="recommendation-list">{recommendations.map(({ resource, distance: distanceKm, fit: match }) => <article key={resource.id}><div><span>{resource.kind}</span><strong>{resource.name}</strong><small>{resource.available} available · {Math.round(distanceKm)} km · {match} capability matches</small></div><button type="button" onClick={() => stage(resource.id)}>Stage</button></article>)}</div>{staged.length > 0 && <div className="staged-note">{staged.length} asset group{staged.length > 1 ? "s" : ""} staged. Remaining options reranked automatically.</div>}</aside>
    </div>

    <section className="ops-section"><div className="ops-card-heading"><div><span className="eyebrow">Response capacity</span><h2>Shelters, volunteers, supplies, and teams</h2></div></div><div className="capacity-grid">{data.resources.map((resource) => <article key={resource.id}><span>{resource.kind}</span><strong>{resource.available.toLocaleString()}</strong><h3>{resource.name}</h3><p>{resource.capabilities.join(" · ")}</p><div><i style={{ width: `${Math.round(resource.available / resource.quantity * 100)}%` }} /></div><small>{Math.round(resource.available / resource.quantity * 100)}% available</small></article>)}</div></section>

    <section className="ops-section"><div className="ops-card-heading"><div><span className="eyebrow">Infrastructure status</span><h2>Critical systems</h2></div><span className="transparency-label">Status provenance shown</span></div><div className="infrastructure-grid">{data.infrastructure.map((system) => <article key={system.id}><span className={`infra-status ${system.status}`}>{system.status}</span><h3>{system.name}</h3><p>{system.detail}</p><small>{system.source} · {new Date(system.updatedAt).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", timeZone: "UTC" })} UTC</small></article>)}</div><p className="safety-note"><strong>Infrastructure transparency:</strong> demo or incident-derived statuses are explicitly labeled and are never presented as verified utility telemetry. Production adapters can replace them without changing the coordination workflow.</p></section>
  </main>;
}
