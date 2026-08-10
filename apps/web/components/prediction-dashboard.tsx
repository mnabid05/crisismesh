import Link from "next/link";

import { intelligenceFor } from "@/lib/demand";
import type { DashboardData } from "@/lib/types";

function percent(value: number) {
  return `${Math.round(value * 100)}%`;
}

function compact(value: number) {
  return new Intl.NumberFormat("en-US", { notation: value >= 10_000 ? "compact" : "standard", maximumFractionDigits: 1 }).format(value);
}

export function PredictionDashboard({ data }: { data: DashboardData }) {
  const incidents = data.incidents.slice().sort((a, b) => {
    const modelCoverage = Number(b.intelligence?.modelVersion.startsWith("neural-demand"))
      - Number(a.intelligence?.modelVersion.startsWith("neural-demand"));
    return modelCoverage || b.riskScore - a.riskScore;
  });
  const focus = incidents[0];
  if (!focus) return <main className="page-shell"><div className="empty-state">No incidents are currently available.</div></main>;
  const intelligence = intelligenceFor(focus, data.resources);
  const demand = intelligence.demand ?? [];
  const shortages = intelligence.shortages ?? [];
  const leadingSignals = intelligence.topSignals.length > 0
    ? intelligence.topSignals.slice(0, 5)
    : [
        { feature: "affected_population", impact: focus.affectedPopulation / 10_000, direction: "raises" as const },
        { feature: `${focus.kind}_response_profile`, impact: focus.riskScore / 10, direction: "raises" as const },
      ];

  return (
    <main className="page-shell">
      <section className="hero-grid">
        <div className="hero-copy">
          <span className="eyebrow">Immediate-response intelligence</span>
          <h1>Estimate what responders need in the next six hours.</h1>
          <p>CrisisMesh converts official incident and weather signals into one immediate demand window, identifies inventory gaps, and feeds those priorities into resource staging.</p>
          <div className="hero-actions"><Link className="button primary" href="#demand">Open demand plan</Link><Link className="button secondary" href="/operations">Stage resources</Link></div>
        </div>
        <div className="system-card demand-window-card">
          <span className={`status-dot ${data.connected ? "online" : "fallback"}`}>{data.connected ? "Live providers connected" : "Scenario fallback active"}</span>
          <strong>6h</strong><small>single immediate-response window</small>
          <div><span>{data.summary.activeIncidents} active signals</span><span>{intelligence.modelVersion}</span></div>
        </div>
      </section>

      <section className="forecast-section" id="demand">
        <div className="section-lead"><div><span className="eyebrow">Priority demand plan</span><h2>{focus.title}</h2><p>{focus.regions.join(" · ")} · observed by {focus.source}</p></div><a href={focus.sourceUrl ?? "#"} target="_blank" rel="noreferrer">Open official source ↗</a></div>
        <div className="prediction-layout">
          <div className="forecast-main">
            <div className="demand-summary">
              <div><span>Six-hour demand index</span><strong>{intelligence.demandIndex ?? Math.round(intelligence.probability * 100)}</strong><small>{intelligence.demandLevel ?? "estimated"} operational pressure</small></div>
              <p>Quantities combine modeled pressure, affected population, and a disclosed factor for each resource category.</p>
            </div>
            <div className="demand-grid">
              {demand.map((item) => {
                const gap = shortages.find((shortage) => shortage.category === item.category);
                return (
                  <article className="demand-card" key={item.category}>
                    <div><span>{item.label}</span><i style={{ width: percent(item.pressure) }} /></div>
                    <strong>{compact(item.quantity)}</strong><small>{item.unit} estimated</small>
                    <p>{compact(item.lower)}–{compact(item.upper)} range · {percent(item.pressure)} pressure</p>
                    {gap?.shortfall != null ? <em className={`gap-label ${gap.urgency}`}>{compact(gap.shortfall)} {item.unit} gap</em> : null}
                  </article>
                );
              })}
            </div>
          </div>
          <aside className="forecast-context">
            <span className="eyebrow">What drives this</span>
            <h3>Leading signals</h3>
            <div className="signal-list">
              {leadingSignals.map((signal) => (
                <div key={signal.feature}><span>{signal.feature.replaceAll("_", " ")}</span><strong className={signal.direction}>{signal.impact > 0 ? "+" : ""}{signal.impact.toFixed(1)}</strong></div>
              ))}
            </div>
            <div className="confidence-note"><strong>{intelligence.confidenceLabel ?? `${Math.round(focus.confidence * 100)}% input confidence`}</strong><p>{intelligence.providerCoverage ? `${intelligence.providerCoverage.available}/${intelligence.providerCoverage.expected} context providers available.` : "Uncertainty widens when source coverage falls."}</p></div>
            <Link className="context-link" href="/operations">Open shortage-aware staging →</Link>
          </aside>
        </div>
        <p className="safety-note"><strong>Planning estimate, not a dispatch order.</strong> {intelligence.disclaimer}</p>
      </section>

      <section className="overview-section">
        <div className="section-lead"><div><span className="eyebrow">Active watchlist</span><h2>Highest immediate demand</h2></div><Link href="/incidents">View all incidents →</Link></div>
        <div className="watchlist">
          {incidents.slice(0, 5).map((incident) => {
            const incidentIntelligence = intelligenceFor(incident, data.resources);
            return <article key={incident.id}><span className={`severity ${incident.severity}`}>{incident.severity}</span><div><strong>{incident.title}</strong><p>{incident.source} · {incident.regions[0]}</p></div><div className="watch-score"><strong>{incidentIntelligence.demandIndex ?? incident.riskScore}</strong><small>6h demand</small></div></article>;
          })}
        </div>
      </section>
    </main>
  );
}
