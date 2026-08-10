import Link from "next/link";

import type { DashboardData, Incident, PredictionHorizon } from "@/lib/types";

function percent(value: number) {
  return `${Math.round(value * 100)}%`;
}

function horizonData(incident: Incident): PredictionHorizon[] {
  return incident.intelligence?.horizons ?? [
    { hours: 6, probability: Math.max(0.03, incident.riskScore / 130), lower: 0.02, upper: Math.min(1, incident.riskScore / 100), level: "baseline" },
    { hours: 24, probability: incident.riskScore / 100, lower: Math.max(0, incident.riskScore / 100 - 0.18), upper: Math.min(1, incident.riskScore / 100 + 0.18), level: "baseline" },
    { hours: 72, probability: Math.min(0.98, incident.riskScore / 100 + 0.08), lower: Math.max(0, incident.riskScore / 100 - 0.12), upper: Math.min(1, incident.riskScore / 100 + 0.2), level: "baseline" },
  ];
}

function PredictionChart({ horizons }: { horizons: PredictionHorizon[] }) {
  const x = [36, 170, 304];
  const y = (value: number) => 148 - value * 112;
  const points = horizons.map((item, index) => `${x[index]},${y(item.probability)}`).join(" ");
  const band = [
    ...horizons.map((item, index) => `${x[index]},${y(item.upper)}`),
    ...horizons.slice().reverse().map((item, reverseIndex) => `${x[2 - reverseIndex]},${y(item.lower)}`),
  ].join(" ");
  return (
    <div className="forecast-chart">
      <div className="chart-title"><span>Escalation trajectory</span><small>Shaded area = uncertainty</small></div>
      <svg viewBox="0 0 340 180" role="img" aria-label="Escalation probability across 6, 24, and 72 hours">
        {[0.25, 0.5, 0.75].map((value) => <line key={value} x1="30" x2="320" y1={y(value)} y2={y(value)} className="grid-line" />)}
        <polygon points={band} className="uncertainty-band" />
        <polyline points={points} className="trajectory-line" />
        {horizons.map((item, index) => <circle key={item.hours} cx={x[index]} cy={y(item.probability)} r="5" />)}
        {horizons.map((item, index) => <text key={item.hours} x={x[index]} y="172" textAnchor="middle">{item.hours}h</text>)}
      </svg>
    </div>
  );
}

export function PredictionDashboard({ data }: { data: DashboardData }) {
  const incidents = data.incidents.slice().sort((a, b) => {
    const modelCoverage = Number(Boolean(b.intelligence)) - Number(Boolean(a.intelligence));
    return modelCoverage || b.riskScore - a.riskScore;
  });
  const focus = incidents[0];
  if (!focus) return <main className="page-shell"><div className="empty-state">No incidents are currently available.</div></main>;
  const horizons = horizonData(focus);
  return (
    <main className="page-shell">
      <section className="hero-grid">
        <div className="hero-copy">
          <span className="eyebrow">Live multi-source intelligence</span>
          <h1>See how an active incident may escalate—before response windows close.</h1>
          <p>CrisisMesh fuses official event feeds with environmental context, then estimates operational escalation at 6, 24, and 72 hours.</p>
          <div className="hero-actions"><Link className="button primary" href="#forecast">View forecast</Link><Link className="button secondary" href="/resources">Preparedness resources</Link></div>
        </div>
        <div className="system-card">
          <span className={`status-dot ${data.connected ? "online" : "fallback"}`}>{data.connected ? "Live providers connected" : "Fallback scenario"}</span>
          <strong>{data.summary.activeIncidents}</strong><small>active signals monitored</small>
          <div><span>{data.summary.sources.length} providers</span><span>Updated {new Date(data.summary.generatedAt).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", timeZone: "UTC" })} UTC</span></div>
        </div>
      </section>

      <section className="forecast-section" id="forecast">
        <div className="section-lead"><div><span className="eyebrow">Priority forecast</span><h2>{focus.title}</h2><p>{focus.regions.join(" · ")} · observed by {focus.source}</p></div><a href={focus.sourceUrl ?? "#"} target="_blank" rel="noreferrer">Open official source ↗</a></div>
        <div className="prediction-layout">
          <div className="forecast-main">
            <div className="horizon-grid">
              {horizons.map((item) => (
                <article className="horizon-card" key={item.hours}>
                  <span>{item.hours} hour outlook</span><strong>{percent(item.probability)}</strong>
                  <p>{item.level} escalation likelihood</p><small>{percent(item.lower)}–{percent(item.upper)} estimated range</small>
                </article>
              ))}
            </div>
            <PredictionChart horizons={horizons} />
          </div>
          <aside className="forecast-context">
            <span className="eyebrow">What drives this</span>
            <h3>Leading signals</h3>
            <div className="signal-list">
              {(focus.intelligence?.topSignals ?? []).slice(0, 5).map((signal) => (
                <div key={signal.feature}><span>{signal.feature.replaceAll("_", " ")}</span><strong className={signal.direction}>{signal.impact > 0 ? "+" : ""}{signal.impact.toFixed(1)}</strong></div>
              ))}
            </div>
            <div className="confidence-note"><strong>{Math.round(focus.confidence * 100)}% input confidence</strong><p>Uncertainty widens when source coverage or input confidence falls.</p></div>
          </aside>
        </div>
        <p className="safety-note"><strong>Decision support, not a warning.</strong> {focus.intelligence?.disclaimer ?? "These estimates are experimental and must not replace instructions from public authorities."}</p>
      </section>

      <section className="overview-section">
        <div className="section-lead"><div><span className="eyebrow">Active watchlist</span><h2>Highest-priority incidents</h2></div><Link href="/incidents">View all incidents →</Link></div>
        <div className="watchlist">
          {incidents.slice(0, 5).map((incident) => (
            <article key={incident.id}><span className={`severity ${incident.severity}`}>{incident.severity}</span><div><strong>{incident.title}</strong><p>{incident.source} · {incident.regions[0]}</p></div><div className="watch-score"><strong>{incident.riskScore}</strong><small>24h index</small></div></article>
          ))}
        </div>
      </section>
    </main>
  );
}
