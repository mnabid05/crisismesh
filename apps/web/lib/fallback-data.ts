import type { DashboardData } from "./types";

const now = new Date();
const ago = (minutes: number) => new Date(now.getTime() - minutes * 60_000).toISOString();

export const fallbackData: DashboardData = {
  connected: false,
  streaming: false,
  dataMode: "scenario",
  incidents: [
    { id: "cm-atlantic-07", title: "Atlantic tropical cyclone watch", kind: "storm", severity: "critical", status: "active", source: "NASA EONET", description: "Rapidly organizing tropical system with coastal flood potential. Emergency managers are reviewing shelter capacity across two counties.", latitude: 26.7, longitude: -74.2, startedAt: ago(540), updatedAt: ago(3), riskScore: 91, confidence: 0.88, affectedPopulation: 184000, regions: ["Broward County", "Miami-Dade"] },
    { id: "cm-gulf-22", title: "Flash flood emergency", kind: "flood", severity: "high", status: "active", source: "NOAA / NWS", description: "Training thunderstorms producing life-threatening flash flooding across low-lying corridors.", latitude: 29.8, longitude: -95.4, startedAt: ago(240), updatedAt: ago(1), riskScore: 84, confidence: 0.96, affectedPopulation: 73000, regions: ["Harris County"] },
    { id: "cm-cascadia-14", title: "Cascadia wildfire complex", kind: "wildfire", severity: "high", status: "active", source: "NASA EONET", description: "Multiple active fire perimeters with smoke affecting two counties and regional highways.", latitude: 44.4, longitude: -121.6, startedAt: ago(1860), updatedAt: ago(7), riskScore: 78, confidence: 0.93, affectedPopulation: 42600, regions: ["Deschutes County", "Jefferson County"] },
    { id: "cm-plains-19", title: "Severe convective outbreak", kind: "storm", severity: "moderate", status: "active", source: "NOAA / NWS", description: "Damaging wind and isolated tornado risk across the central plains.", latitude: 38.7, longitude: -97.2, startedAt: ago(360), updatedAt: ago(8), riskScore: 66, confidence: 0.81, affectedPopulation: 97500, regions: ["Saline County", "McPherson County"] },
    { id: "cm-sierra-03", title: "M4.8 regional earthquake", kind: "earthquake", severity: "moderate", status: "monitoring", source: "USGS", description: "Shallow earthquake with light-to-moderate reported shaking.", latitude: 37.5, longitude: -118.8, startedAt: ago(120), updatedAt: ago(11), riskScore: 53, confidence: 0.99, affectedPopulation: 12800, regions: ["Mono County"] },
  ],
  resources: [
    { id: "res-usar-01", name: "Urban Search & Rescue 01", kind: "rescue", status: "ready", quantity: 42, available: 32, latitude: 33.75, longitude: -84.39, capabilities: ["medical", "swift-water", "structural"], demandCategory: "rescue_teams", unit: "teams" },
    { id: "res-med-07", name: "Mobile Medical Unit 07", kind: "medical", status: "ready", quantity: 18, available: 12, latitude: 30.27, longitude: -97.74, capabilities: ["triage", "critical-care"], demandCategory: "medical_teams", unit: "teams" },
    { id: "res-air-03", name: "Regional Evacuation Fleet", kind: "transport", status: "partial", quantity: 640, available: 420, latitude: 32.9, longitude: -80.0, capabilities: ["evacuation", "accessible-transport", "cargo"], demandCategory: "transport_seats", unit: "seats" },
    { id: "res-shelter-12", name: "Shelter Support 12", kind: "shelter", status: "ready", quantity: 600, available: 480, latitude: 28.54, longitude: -81.38, capabilities: ["cots", "meals", "accessibility"], demandCategory: "shelter_beds", unit: "beds" },
    { id: "res-volunteer-04", name: "Community Volunteer Network", kind: "volunteer", status: "ready", quantity: 230, available: 186, latitude: 29.76, longitude: -95.37, capabilities: ["wellness-checks", "distribution", "translation"] },
    { id: "res-supply-09", name: "Regional Meal Cache 09", kind: "supplies", status: "ready", quantity: 150000, available: 112000, latitude: 35.22, longitude: -80.84, capabilities: ["meals", "distribution"], demandCategory: "meals", unit: "meals" },
    { id: "res-water-05", name: "Potable Water Cache 05", kind: "supplies", status: "ready", quantity: 180000, available: 126000, latitude: 34.75, longitude: -92.29, capabilities: ["water", "distribution"], demandCategory: "water_liters", unit: "liters" },
  ],
  infrastructure: [
    { id: "infra-power-01", name: "Regional power network", kind: "power", status: "monitoring", detail: "Weather exposure elevated; no verified outage feed connected.", source: "Coordination demo layer", updatedAt: ago(4) },
    { id: "infra-road-01", name: "Primary transport corridors", kind: "transport", status: "impaired", detail: "Flood and fire incidents may affect routing; verify with local DOT sources.", source: "Incident-derived status", updatedAt: ago(6) },
    { id: "infra-comms-01", name: "Emergency communications", kind: "communications", status: "operational", detail: "Coordination channel available in the demonstration workspace.", source: "Coordination demo layer", updatedAt: ago(2) },
    { id: "infra-water-01", name: "Public water systems", kind: "water", status: "monitoring", detail: "No live utility adapter connected; status is not authoritative.", source: "Integration placeholder", updatedAt: ago(12) },
  ],
  summary: {
    activeIncidents: 4,
    criticalIncidents: 1,
    affectedPopulation: 409900,
    resourcesAvailable: 239130,
    openDeployments: 3,
    meanRiskScore: 74.5,
    byKind: { storm: 2, flood: 1, wildfire: 1, earthquake: 1 },
    sources: [
      { name: "NASA EONET", status: "operational", lastSync: ago(1), lagSeconds: 42 },
      { name: "NOAA / NWS", status: "operational", lastSync: ago(1), lagSeconds: 18 },
      { name: "USGS", status: "operational", lastSync: ago(1), lagSeconds: 31 },
    ],
    generatedAt: now.toISOString(),
  },
};
