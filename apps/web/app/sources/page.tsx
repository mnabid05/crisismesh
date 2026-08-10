import { getDashboardData } from "@/lib/api";

const providerDetails = {
  "NASA EONET": ["Natural event discovery", "https://eonet.gsfc.nasa.gov/"],
  "NOAA / NWS": ["United States weather alerts", "https://www.weather.gov/documentation/services-web-api"],
  USGS: ["Near-real-time earthquakes", "https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php"],
} as const;

export default async function SourcesPage() {
  const data = await getDashboardData();
  return <main className="page-shell subpage"><div className="page-heading"><span className="eyebrow">Provenance and reliability</span><h1>Every signal keeps its source.</h1><p>CrisisMesh uses independent providers and preserves partial results if one is delayed. Runtime environmental context comes from Open-Meteo and NASA POWER.</p></div><div className="resource-grid">{data.summary.sources.map((source) => { const detail = providerDetails[source.name as keyof typeof providerDetails]; return <a href={detail?.[1] ?? "#"} target="_blank" rel="noreferrer" key={source.name}><span>{source.status}</span><h2>{source.name}</h2><p>{detail?.[0] ?? "Operational data source"}. Last synchronization: {new Date(source.lastSync).toLocaleString("en-US", { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" })} UTC.</p><strong>Read provider documentation ↗</strong></a>; })}<a href="https://open-meteo.com/en/docs" target="_blank" rel="noreferrer"><span>Environmental enrichment</span><h2>Open-Meteo</h2><p>Best-match forecast context with bounded timeouts and a coordinate-keyed cache.</p><strong>Read provider documentation ↗</strong></a><a href="https://power.larc.nasa.gov/docs/services/api/" target="_blank" rel="noreferrer"><span>Environmental enrichment</span><h2>NASA POWER</h2><p>Recent daily meteorology used as climate context, cached on a half-degree grid.</p><strong>Read provider documentation ↗</strong></a></div></main>;
}
