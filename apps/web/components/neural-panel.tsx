import type { Incident } from "@/lib/types";
import { Icon } from "./icons";

const label = (value: string) => value.replaceAll("_", " ");

export function NeuralPanel({ incident }: { incident: Incident }) {
  const intelligence = incident.intelligence;
  return (
    <section className="neural-panel" aria-labelledby="neural-heading">
      <div className="section-heading">
        <div>
          <span className="eyebrow">NEURAL FUSION</span>
          <h2 id="neural-heading">Signal reasoning</h2>
        </div>
        <Icon name="activity" />
      </div>
      {!intelligence ? (
        <div className="neural-empty">
          <span className="neural-orb idle" />
          <div>
            <strong>Baseline model active</strong>
            <p>Live environmental enrichment is unavailable for this signal.</p>
          </div>
        </div>
      ) : (
        <div className="neural-content">
          <div className="model-row">
            <span className="neural-orb" />
            <div><strong>{intelligence.modelVersion}</strong><small>18 → 12 → 1 feed-forward network</small></div>
            <b>{Math.round(intelligence.probability * 100)}%</b>
          </div>
          <div className="environment-grid" aria-label="Environmental signals">
            <div><Icon name="weather" /><span>Temperature</span><strong>{intelligence.environment.temperature_c.toFixed(1)}°C</strong></div>
            <div><Icon name="radio" /><span>Precipitation</span><strong>{intelligence.environment.precipitation_mm.toFixed(1)} mm</strong></div>
            <div><Icon name="route" /><span>Wind gust</span><strong>{intelligence.environment.wind_gust_kph.toFixed(0)} km/h</strong></div>
          </div>
          <div className="signal-stack">
            {intelligence.topSignals.slice(0, 4).map((signal) => (
              <div className="signal-row" key={signal.feature}>
                <span>{label(signal.feature)}</span>
                <i><b className={signal.direction} style={{ width: `${Math.min(100, Math.abs(signal.impact) * 8 + 8)}%` }} /></i>
                <strong className={signal.direction}>{signal.impact > 0 ? "+" : ""}{signal.impact.toFixed(1)}</strong>
              </div>
            ))}
          </div>
          <div className="provider-pills">
            <span>{intelligence.environment.forecast_source}</span>
            <span>{intelligence.environment.climate_source}</span>
          </div>
          <p className="model-disclaimer"><Icon name="alert" />{intelligence.disclaimer}</p>
        </div>
      )}
    </section>
  );
}
