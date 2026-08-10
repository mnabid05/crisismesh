import { fallbackData } from "./fallback-data";
import type {
  DashboardData,
  Incident,
  NeuralInsight,
  Severity,
  SourceHealth,
} from "./types";

const EONET_URL = "https://eonet.gsfc.nasa.gov/api/v3/events?status=open&days=30&limit=40";
const NWS_URL = "https://api.weather.gov/alerts/active?status=actual&message_type=alert";
const USGS_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_day.geojson";
const intelligenceUrl =
  process.env.INTELLIGENCE_URL ??
  process.env.NEXT_PUBLIC_INTELLIGENCE_URL ??
  "http://localhost:8090";

interface EonetPayload {
  events: Array<{
    id: string;
    title: string;
    description?: string;
    link?: string;
    categories?: Array<{ id: string; title: string }>;
    geometry?: Array<{ date: string; coordinates: number[] }>;
  }>;
}

interface NwsPayload {
  features: Array<{
    id: string;
    geometry?: { coordinates?: unknown };
    properties: {
      event?: string;
      severity?: string;
      description?: string;
      areaDesc?: string;
      web?: string;
      sent?: string;
    };
  }>;
}

interface UsgsPayload {
  features: Array<{
    id: string;
    properties: {
      mag?: number;
      place?: string;
      url?: string;
      time?: number;
      sig?: number;
      alert?: string | null;
      tsunami?: number;
    };
    geometry?: { coordinates?: number[] };
  }>;
}

interface PredictionResponse extends NeuralInsight {
  target: string;
  confidence: number;
  horizons: NonNullable<NeuralInsight["horizons"]>;
  provenance: NonNullable<NeuralInsight["provenance"]>;
}

async function fetchJSON<T>(url: string, headers: HeadersInit = {}): Promise<T> {
  const response = await fetch(url, {
    headers: { Accept: "application/json", ...headers },
    next: { revalidate: 300 },
    signal: AbortSignal.timeout(5500),
  });
  if (!response.ok) throw new Error(`${new URL(url).hostname} returned ${response.status}`);
  return response.json() as Promise<T>;
}

function normalizeKind(value: string): string {
  const normalized = value.toLowerCase();
  if (normalized.includes("fire")) return "wildfire";
  if (normalized.includes("flood")) return "flood";
  if (normalized.includes("storm") || normalized.includes("cyclone") || normalized.includes("hurricane")) return "storm";
  if (normalized.includes("earthquake")) return "earthquake";
  if (normalized.includes("volcano")) return "volcano";
  return "other";
}

function normalizeSeverity(value: string | undefined): Severity {
  switch (value?.toLowerCase()) {
    case "extreme": return "critical";
    case "severe": return "high";
    case "moderate": return "moderate";
    default: return "low";
  }
}

function baselineRisk(severity: Severity, kind: string, magnitude = 0): number {
  const base = { critical: 88, high: 75, moderate: 58, low: 37 }[severity];
  if (kind === "earthquake") return Math.min(96, Math.max(base, 34 + magnitude * 8));
  return base;
}

function estimatedExposure(severity: Severity, kind: string): number {
  const severityFactor = { critical: 8, high: 4, moderate: 2, low: 1 }[severity];
  const kindFactor = kind === "storm" || kind === "flood" ? 1.8 : kind === "wildfire" ? 0.7 : 0.45;
  return Math.round(7_500 * severityFactor * kindFactor);
}

function trim(value: string | undefined, length = 300): string {
  const text = value?.trim() || "Provider event is active; consult the linked official source for details.";
  return text.length > length ? `${text.slice(0, length - 1)}…` : text;
}

function centroid(value: unknown): [number, number] | null {
  const points: Array<[number, number]> = [];
  const collect = (item: unknown): void => {
    if (points.length >= 1000 || !Array.isArray(item)) return;
    if (item.length >= 2 && typeof item[0] === "number" && typeof item[1] === "number") {
      points.push([item[1], item[0]]);
      return;
    }
    item.forEach(collect);
  };
  collect(value);
  if (points.length === 0) return null;
  const total = points.reduce(([lat, lon], [pointLat, pointLon]) => [lat + pointLat, lon + pointLon], [0, 0]);
  return [total[0] / points.length, total[1] / points.length];
}

async function loadEonet(): Promise<Incident[]> {
  const payload = await fetchJSON<EonetPayload>(EONET_URL);
  return payload.events.flatMap((event) => {
    const geometry = event.geometry?.at(-1);
    if (!geometry || geometry.coordinates.length < 2) return [];
    const kind = normalizeKind(event.categories?.[0]?.id ?? "other");
    const severity: Severity = "moderate";
    const timestamp = geometry.date || new Date().toISOString();
    return [{
      id: `eonet-${event.id}`,
      externalId: event.id,
      title: event.title,
      kind,
      severity,
      status: "active" as const,
      source: "NASA EONET",
      sourceUrl: event.link,
      description: trim(event.description, 280),
      latitude: geometry.coordinates[1],
      longitude: geometry.coordinates[0],
      startedAt: timestamp,
      updatedAt: timestamp,
      riskScore: baselineRisk(severity, kind),
      confidence: 0.82,
      affectedPopulation: estimatedExposure(severity, kind),
      regions: [event.categories?.[0]?.title ?? "Global event"],
    }];
  });
}

async function loadNws(): Promise<Incident[]> {
  const payload = await fetchJSON<NwsPayload>(NWS_URL, {
    "User-Agent": process.env.NWS_USER_AGENT ?? "CrisisMesh/0.2 portfolio@example.com",
  });
  return payload.features.slice(0, 80).flatMap((feature) => {
    const location = centroid(feature.geometry?.coordinates);
    if (!location) return [];
    const title = feature.properties.event ?? "NWS weather alert";
    const kind = normalizeKind(title);
    const severity = normalizeSeverity(feature.properties.severity);
    const timestamp = feature.properties.sent ?? new Date().toISOString();
    return [{
      id: `nws-${feature.id.split("/").at(-1)}`,
      externalId: feature.id,
      title,
      kind,
      severity,
      status: "active" as const,
      source: "NOAA / NWS",
      sourceUrl: feature.properties.web,
      description: trim(feature.properties.description),
      latitude: location[0],
      longitude: location[1],
      startedAt: timestamp,
      updatedAt: timestamp,
      riskScore: baselineRisk(severity, kind),
      confidence: 0.96,
      affectedPopulation: estimatedExposure(severity, kind),
      regions: feature.properties.areaDesc?.split(";").slice(0, 3).map((item) => item.trim()) ?? [],
    }];
  });
}

async function loadUsgs(): Promise<Incident[]> {
  const payload = await fetchJSON<UsgsPayload>(USGS_URL);
  return payload.features.flatMap((feature) => {
    const coordinates = feature.geometry?.coordinates;
    if (!coordinates || coordinates.length < 2) return [];
    const magnitude = feature.properties.mag ?? 0;
    const severity: Severity = magnitude >= 6 ? "critical" : magnitude >= 5 ? "high" : "moderate";
    const timestamp = new Date(feature.properties.time ?? Date.now()).toISOString();
    return [{
      id: `usgs-${feature.id}`,
      externalId: feature.id,
      title: `M${magnitude.toFixed(1)} earthquake — ${feature.properties.place ?? "location pending"}`,
      kind: "earthquake",
      severity,
      status: "monitoring" as const,
      source: "USGS",
      sourceUrl: feature.properties.url,
      description: "Automated earthquake signal from the USGS near-real-time GeoJSON feed.",
      latitude: coordinates[1],
      longitude: coordinates[0],
      startedAt: timestamp,
      updatedAt: timestamp,
      riskScore: baselineRisk(severity, "earthquake", magnitude),
      confidence: 0.99,
      affectedPopulation: estimatedExposure(severity, "earthquake"),
      regions: [feature.properties.place ?? "Region pending"],
      metadata: {
        magnitude,
        depth: coordinates[2] ?? 0,
        significance: feature.properties.sig ?? 0,
        alert: feature.properties.alert ?? "",
        tsunami: feature.properties.tsunami === 1,
      },
    }];
  });
}

async function addNeuralScore(incident: Incident): Promise<Incident> {
  try {
    const response = await fetch(`${intelligenceUrl.replace(/\/$/, "")}/v2/predictions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ incident }),
      cache: "no-store",
      signal: AbortSignal.timeout(9500),
    });
    if (!response.ok) return incident;
    const neural = await response.json() as PredictionResponse;
    const day = neural.horizons.find((horizon) => horizon.hours === 24) ?? neural.horizons[0];
    return {
      ...incident,
      riskScore: Math.round((day?.probability ?? incident.riskScore / 100) * 100),
      confidence: neural.confidence,
      intelligence: {
        probability: day?.probability ?? incident.riskScore / 100,
        modelVersion: neural.modelVersion,
        modelKind: neural.modelKind,
        topSignals: neural.topSignals,
        environment: neural.environment,
        disclaimer: neural.disclaimer,
        horizons: neural.horizons,
        target: neural.target,
        provenance: neural.provenance,
      },
    };
  } catch {
    return incident;
  }
}

function sourceHealth(name: string, result: PromiseSettledResult<Incident[]>): SourceHealth {
  return {
    name,
    status: result.status === "fulfilled" ? "healthy" : "delayed",
    lastSync: new Date().toISOString(),
    lagSeconds: result.status === "fulfilled" ? 0 : 300,
  };
}

export async function getLiveFusionData(): Promise<DashboardData | null> {
  const results = await Promise.allSettled([loadEonet(), loadNws(), loadUsgs()]);
  const incidents = results
    .flatMap((result) => result.status === "fulfilled" ? result.value : [])
    .sort((left, right) => right.riskScore - left.riskScore || right.updatedAt.localeCompare(left.updatedAt))
    .slice(0, 12);
  if (incidents.length === 0) return null;

  const scored = await Promise.all(incidents.slice(0, 6).map(addNeuralScore));
  const fused = [...scored, ...incidents.slice(6)];
  const resources = fallbackData.resources;
  const sources = [
    sourceHealth("NASA EONET", results[0]),
    sourceHealth("NOAA / NWS", results[1]),
    sourceHealth("USGS", results[2]),
  ];
  return {
    connected: true,
    streaming: false,
    dataMode: "live-fusion",
    incidents: fused,
    resources,
    summary: {
      activeIncidents: fused.length,
      criticalIncidents: fused.filter((item) => item.severity === "critical").length,
      affectedPopulation: fused.reduce((total, item) => total + item.affectedPopulation, 0),
      resourcesAvailable: resources.reduce((total, item) => total + item.available, 0),
      openDeployments: 0,
      meanRiskScore: fused.reduce((total, item) => total + item.riskScore, 0) / fused.length,
      byKind: Object.fromEntries(
        [...new Set(fused.map((item) => item.kind))].map((kind) => [kind, fused.filter((item) => item.kind === kind).length]),
      ),
      sources,
      generatedAt: new Date().toISOString(),
    },
  };
}
