import type { Incident } from "@/lib/types";
import { Icon } from "./icons";

const utc = (value: string) => `${value.slice(11, 16)}Z`;

export function IncidentList({ incidents, selectedId, onSelect }: { incidents: Incident[]; selectedId: string; onSelect: (id: string) => void }) {
  return (
    <section className="incident-list-panel">
      <div className="section-heading"><div><span className="eyebrow">PRIORITY QUEUE</span><h2>Active signals</h2></div><span className="record-count">{String(incidents.length).padStart(2, "0")}</span></div>
      <div className="incident-list">
        {incidents.map((incident, index) => (
          <button type="button" key={incident.id} className={`incident-row ${selectedId === incident.id ? "selected" : ""}`} aria-current={selectedId === incident.id ? "true" : undefined} onClick={() => onSelect(incident.id)}>
            <span className={`severity-index ${incident.severity}`}>{String(index + 1).padStart(2, "0")}</span>
            <span className="incident-copy"><span className="incident-meta"><b>{incident.kind}</b><i />{incident.source}</span><strong>{incident.title}</strong><small>{incident.regions.join(" · ")}</small></span>
            <span className="incident-score"><b>{Math.round(incident.riskScore)}</b><time dateTime={incident.updatedAt}>{utc(incident.updatedAt)}</time><Icon name="chevron" /></span>
          </button>
        ))}
        {incidents.length === 0 && <div className="empty-state">No incidents match this filter.</div>}
      </div>
    </section>
  );
}
