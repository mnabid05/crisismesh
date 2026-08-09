export type Severity = "critical" | "high" | "moderate" | "low";
export type IncidentStatus = "active" | "monitoring" | "contained";

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
}

export interface SourceHealth {
  name: string;
  status: string;
  lastSync: string;
  lagSeconds: number;
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
}

