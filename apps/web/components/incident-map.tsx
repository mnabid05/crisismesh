import type { Incident, Resource } from "@/lib/types";
import { Icon } from "./icons";

function project(latitude: number, longitude: number) {
  return { left: `${Math.max(2, Math.min(98, ((longitude + 130) / 65) * 100))}%`, top: `${Math.max(3, Math.min(96, ((50 - latitude) / 26) * 100))}%` };
}

export function IncidentMap({ incidents, resources, selectedId, onSelect }: { incidents: Incident[]; resources: Resource[]; selectedId: string; onSelect: (id: string) => void }) {
  return (
    <section className="map-panel" aria-label="Incident map">
      <div className="map-toolbar">
        <div><span className="eyebrow">COMMON OPERATING PICTURE</span><h2>Live incident field</h2></div>
        <div className="map-tools"><button aria-label="Center map"><Icon name="locate" /></button><button aria-label="Map layers"><Icon name="layers" /></button></div>
      </div>
      <div className="map-canvas">
        <svg className="map-shape" viewBox="0 0 1000 600" role="img" aria-label="Simplified map of the contiguous United States">
          <defs><pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="currentColor" strokeWidth=".5" /></pattern></defs>
          <rect width="1000" height="600" fill="url(#grid)" />
          <path className="land" d="M85 88 173 64l70 31 95-10 90 21 87-2 66 27 92-10 83 36 76 5 78 55-12 64-58 47-22 63-54 10-43 73-43-2-11-79-39-22-30-71-78-34-63 28-90-2-56 27-57-61-68-11-48-59-41-5-27-83Z" />
          <path className="state-line" d="M185 82l-12 205M260 94l-8 235M345 87l5 245M438 106l5 233M526 105l-4 264M616 127l-12 270M705 123l-12 305M790 160l-27 230M91 170l730 11M101 245l700 19M133 321l620 25M204 394l510 20" />
        </svg>
        <div className="map-label label-pacific">PACIFIC</div><div className="map-label label-atlantic">ATLANTIC</div><div className="map-label label-gulf">GULF OF MEXICO</div>
        {resources.map((resource) => <span key={resource.id} className="resource-marker" style={project(resource.latitude, resource.longitude)} title={resource.name}><Icon name="shield" /></span>)}
        {incidents.map((incident) => (
          <button key={incident.id} className={`incident-marker ${incident.severity} ${selectedId === incident.id ? "selected" : ""}`} style={project(incident.latitude, incident.longitude)} onClick={() => onSelect(incident.id)} aria-label={`Select ${incident.title}`}>
            <span className="marker-pulse" /><span className="marker-core">{Math.round(incident.riskScore)}</span>
            {selectedId === incident.id && <span className="marker-label"><b>{incident.kind}</b>{incident.title}</span>}
          </button>
        ))}
        <div className="map-legend"><span><i className="legend-dot critical" />Critical</span><span><i className="legend-dot high" />High</span><span><i className="legend-dot moderate" />Monitored</span><span><Icon name="shield" />Resource</span></div>
      </div>
    </section>
  );
}

