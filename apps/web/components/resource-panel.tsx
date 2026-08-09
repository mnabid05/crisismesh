import type { Allocation, Resource } from "@/lib/types";
import { Icon } from "./icons";

function allocationFor(resourceId: string, allocations: Allocation[]) { return allocations.find((item) => item.resourceId === resourceId); }

export function ResourcePanel({ resources, allocations }: { resources: Resource[]; allocations: Allocation[] }) {
  return (
    <section className="resource-panel">
      <div className="section-heading"><div><span className="eyebrow">RESPONSE NETWORK</span><h2>Deployable assets</h2></div><Icon name="route" /></div>
      <div className="resource-list">
        {resources.map((resource) => {
          const allocation = allocationFor(resource.id, allocations);
          return <article className="resource-row" key={resource.id}>
            <div className="resource-icon"><Icon name={resource.kind === "medical" ? "activity" : resource.kind === "aviation" ? "weather" : "shield"} /></div>
            <div className="resource-copy"><strong>{resource.name}</strong><span>{resource.capabilities.slice(0, 2).join(" · ")}</span>{allocation && <small>{Math.round(allocation.etaSeconds / 60)} min ETA · {allocation.suitability.toFixed(2)} match</small>}</div>
            <div className="resource-availability"><b>{resource.available}</b><span>ready</span></div>
          </article>;
        })}
      </div>
    </section>
  );
}

