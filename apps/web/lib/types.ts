export type Severity = "critical" | "high" | "moderate" | "low";
export type IncidentStatus = "active" | "monitoring" | "contained";
export type DataMode = "operations" | "live-fusion" | "scenario";

export interface NeuralSignal {
  feature: string;
  impact: number;
  direction: "raises" | "reduces";
}

export interface EnvironmentSnapshot {
  temperature_c: number;
  precipitation_mm: number;
  wind_speed_kph: number;
  wind_gust_kph: number;
  humidity_percent: number;
  cape_jkg: number;
  power_temperature_c: number;
  power_precipitation_mm: number;
  power_wind_speed_ms: number;
  forecast_source: string;
  climate_source: string;
}

export interface NeuralInsight {
  probability: number;
  modelVersion: string;
  modelKind: string;
  topSignals: NeuralSignal[];
  environment: EnvironmentSnapshot;
  disclaimer: string;
  horizons?: PredictionHorizon[];
  target?: string;
  provenance?: { training: string[]; runtime: string[] };
  trajectory?: "rising" | "steady";
  confidenceLabel?: string;
  providerCoverage?: {
    available: number;
    expected: number;
    ratio: number;
    sources: string[];
    missing: string[];
  };
  windowHours?: number;
  demandIndex?: number;
  demandLevel?: string;
  demand?: DemandEstimate[];
  shortages?: ShortageEstimate[];
  inventoryProvided?: boolean;
  planningBasis?: {
    affectedPopulation: number;
    quantityMethod: string;
    labelType: string;
  };
}

export type DemandCategory =
  | "shelter_beds"
  | "medical_teams"
  | "rescue_teams"
  | "water_liters"
  | "meals"
  | "transport_seats";

export interface DemandEstimate {
  category: DemandCategory;
  label: string;
  unit: string;
  pressure: number;
  quantity: number;
  lower: number;
  upper: number;
}

export interface ShortageEstimate extends DemandEstimate {
  available: number | null;
  shortfall: number | null;
  coverage: number | null;
  urgency: "critical" | "high" | "moderate" | "covered" | "unknown";
}

export interface PredictionHorizon {
  hours: number;
  probability: number;
  lower: number;
  upper: number;
  level: string;
}

export interface Incident {
  id: string;
  externalId?: string;
  title: string;
  kind: string;
  severity: Severity;
  status: IncidentStatus;
  source: string;
  sourceUrl?: string;
  description: string;
  latitude: number;
  longitude: number;
  startedAt: string;
  updatedAt: string;
  riskScore: number;
  confidence: number;
  affectedPopulation: number;
  regions: string[];
  intelligence?: NeuralInsight;
  metadata?: Record<string, string | number | boolean | null>;
}

export interface Resource {
  id: string;
  name: string;
  kind: string;
  status: string;
  quantity: number;
  available: number;
  latitude: number;
  longitude: number;
  capabilities: string[];
  demandCategory?: DemandCategory;
  unit?: string;
}

export interface SourceHealth {
  name: string;
  status: string;
  lastSync: string;
  lagSeconds: number;
}

export interface InfrastructureStatus {
  id: string;
  name: string;
  kind: "power" | "transport" | "communications" | "water";
  status: "operational" | "monitoring" | "impaired" | "offline";
  detail: string;
  source: string;
  updatedAt: string;
}

export interface Summary {
  activeIncidents: number;
  criticalIncidents: number;
  affectedPopulation: number;
  resourcesAvailable: number;
  openDeployments: number;
  meanRiskScore: number;
  byKind: Record<string, number>;
  sources: SourceHealth[];
  generatedAt: string;
}

export interface Allocation {
  id: string;
  incidentId: string;
  resourceId: string;
  units: number;
  etaSeconds: number;
  distanceKm: number;
  suitability: number;
  rationale: string;
  status: string;
  createdAt: string;
}

export interface DashboardData {
  incidents: Incident[];
  resources: Resource[];
  summary: Summary;
  connected: boolean;
  streaming: boolean;
  dataMode: DataMode;
  infrastructure: InfrastructureStatus[];
}
