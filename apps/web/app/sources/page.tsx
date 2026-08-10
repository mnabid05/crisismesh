import { getDashboardData } from "@/lib/api";

const providerDetails = {
  "NASA EONET": ["Natural event discovery", "https://eonet.gsfc.nasa.gov/"],
  "NOAA / NWS": ["United States weather alerts", "https://www.weather.gov/documentation/services-web-api"],
  USGS: ["Near-real-time earthquakes", "https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php"],
} as const;

export default async function SourcesPage() {
  const data = await getDashboardData();
  const statuses = Object.fromEntries(
    ["healthy", "delayed", "stale", "unavailable"].map((status) => [
      status,
      data.summary.sources.filter((source) => source.status === status).length,
    ]),
  );
  return <main className="page-shell subpage">
    <div className="page-heading"><span className="eyebrow">Provenance and reliability</span><h1>Every signal keeps its source.</h1><p>CrisisMesh preserves partial results, classifies freshness, and separates event feeds, runtime context, and historical training evidence.</p></div>
    <div className="source-health-strip" aria-label="Provider health summary">{Object.entries(statuses).map(([status, count]) => <div key={status}><span>{status}</span><strong>{count}</strong></div>)}</div>
    <div className="section-lead source-section-lead"><div><span className="eyebrow">Runtime providers</span><h2>Current operational evidence</h2></div><span>{data.dataMode}</span></div>
    <div className="resource-grid">{data.summary.sources.map((source) => { const detail = providerDetails[source.name as keyof typeof providerDetails]; return <a href={detail?.[1] ?? "#"} target="_blank" rel="noreferrer" key={source.name}><span>{source.status} · {source.lagSeconds}s lag</span><h2>{source.name}</h2><p>{detail?.[0] ?? "Operational data source"}. Last synchronization: {new Date(source.lastSync).toLocaleString("en-US", { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" })} UTC.</p><strong>Read provider documentation ↗</strong></a>; })}<a href="https://open-meteo.com/en/docs" target="_blank" rel="noreferrer"><span>Forecast enrichment</span><h2>Open-Meteo</h2><p>Best-match forecast context with bounded retries, timeouts, and a coordinate-keyed cache.</p><strong>Read provider documentation ↗</strong></a><a href="https://power.larc.nasa.gov/docs/services/api/" target="_blank" rel="noreferrer"><span>Climate enrichment</span><h2>NASA POWER</h2><p>Recent daily meteorology cached on a half-degree grid.</p><strong>Read provider documentation ↗</strong></a></div>
    <div className="section-lead source-section-lead"><div><span className="eyebrow">Training provenance</span><h2>Historical outcome evidence</h2></div></div>
    <div className="model-grid"><article><span>NOAA Storm Events 2025</span><h2>Weather impact evidence</h2><p>Injuries, deaths, duration, and normalized damage inform documented pressure proxies. Source archive SHA-256 is recorded by the reproducible dataset manifest.</p></article><article><span>USGS Earthquake Catalog 2025</span><h2>Earthquake impact evidence</h2><p>Magnitude, depth, significance, felt reports, intensity, tsunami, and alert fields inform earthquake pressure proxies from the FDSN catalog.</p></article><article><span>FEMA ESF #6</span><h2>Response category taxonomy</h2><p>Mass-care guidance defines the shelter, feeding, emergency-assistance, and transport categories. It supplies taxonomy—not supervised utilization labels.</p></article><article><span>Explicit planning assumptions</span><h2>Proxy labels, not dispatch truth</h2><p>Historical feeds do not contain six-hour resource request counts. CrisisMesh exposes the proxy-label and quantity-factor boundary in its model card and training note.</p></article></div>
  </main>;
}
