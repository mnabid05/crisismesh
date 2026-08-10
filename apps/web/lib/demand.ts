import type {
  DemandCategory,
  DemandEstimate,
  EnvironmentSnapshot,
  Incident,
  NeuralInsight,
  Resource,
  ShortageEstimate,
} from "./types";

const catalog: Record<DemandCategory, { label: string; unit: string; factor: number }> = {
  shelter_beds: { label: "Shelter beds", unit: "beds", factor: 0.18 },
  medical_teams: { label: "Medical teams", unit: "teams", factor: 0.00008 },
  rescue_teams: { label: "Rescue teams", unit: "teams", factor: 0.000067 },
  water_liters: { label: "Potable water", unit: "liters", factor: 1.5 },
  meals: { label: "Prepared meals", unit: "meals", factor: 1.5 },
  transport_seats: { label: "Evacuation seats", unit: "seats", factor: 0.12 },
};

const profiles: Record<string, Record<DemandCategory, number>> = {
  storm: { shelter_beds: 0.78, medical_teams: 0.42, rescue_teams: 0.48, water_liters: 0.72, meals: 0.82, transport_seats: 0.74 },
  flood: { shelter_beds: 0.76, medical_teams: 0.52, rescue_teams: 1, water_liters: 0.94, meals: 0.8, transport_seats: 0.88 },
  wildfire: { shelter_beds: 0.72, medical_teams: 0.66, rescue_teams: 0.46, water_liters: 0.78, meals: 0.76, transport_seats: 1 },
  earthquake: { shelter_beds: 0.84, medical_teams: 0.92, rescue_teams: 1, water_liters: 0.82, meals: 0.78, transport_seats: 0.86 },
  other: { shelter_beds: 0.5, medical_teams: 0.6, rescue_teams: 0.42, water_liters: 0.58, meals: 0.56, transport_seats: 0.48 },
};

const unavailableEnvironment: EnvironmentSnapshot = {
  temperature_c: 20,
  precipitation_mm: 0,
  wind_speed_kph: 0,
  wind_gust_kph: 0,
  humidity_percent: 50,
  cape_jkg: 0,
  power_temperature_c: 20,
  power_precipitation_mm: 0,
  power_wind_speed_ms: 0,
  forecast_source: "unavailable",
  climate_source: "unavailable",
};

function quantity(category: DemandCategory, population: number, pressure: number) {
  const estimate = Math.round(population * catalog[category].factor * pressure);
  if ((category === "medical_teams" || category === "rescue_teams") && population > 0 && pressure >= 0.1) {
    return Math.max(1, estimate);
  }
  return estimate;
}

export function buildPlanningBaseline(incident: Incident, resources: Resource[]): NeuralInsight {
  const profile = profiles[incident.kind] ?? profiles.other;
  const categories = Object.keys(catalog) as DemandCategory[];
  const base = Math.max(0.08, Math.min(0.92, incident.riskScore / 100));
  const demand: DemandEstimate[] = categories.map((category) => {
    const pressure = Math.min(1, base * (0.42 + profile[category] * 0.58));
    const lowerPressure = Math.max(0, pressure - 0.16);
    const upperPressure = Math.min(1, pressure + 0.16);
    return {
      category,
      label: catalog[category].label,
      unit: catalog[category].unit,
      pressure,
      quantity: quantity(category, incident.affectedPopulation, pressure),
      lower: quantity(category, incident.affectedPopulation, lowerPressure),
      upper: quantity(category, incident.affectedPopulation, upperPressure),
    };
  });
  const inventory = Object.fromEntries(categories.map((category) => [
    category,
    resources
      .filter((resource) => resource.demandCategory === category)
      .reduce((total, resource) => total + resource.available, 0),
  ])) as Record<DemandCategory, number>;
  const shortages: ShortageEstimate[] = demand.map((item) => {
    const available = inventory[item.category];
    const shortfall = Math.max(0, item.quantity - available);
    const gapRatio = shortfall / Math.max(1, item.quantity);
    const urgency: ShortageEstimate["urgency"] = gapRatio >= 0.75 ? "critical" : gapRatio >= 0.4 ? "high" : gapRatio > 0 ? "moderate" : "covered";
    return {
      ...item,
      available,
      shortfall,
      coverage: Math.min(1, available / Math.max(1, item.quantity)),
      urgency,
    };
  }).sort((left, right) => (right.shortfall ?? 0) / Math.max(1, right.quantity) - (left.shortfall ?? 0) / Math.max(1, left.quantity));
  const demandIndex = Math.round(demand.reduce((total, item) => total + item.pressure, 0) / demand.length * 100);
  return {
    probability: demandIndex / 100,
    demandIndex,
    demandLevel: demandIndex >= 65 ? "critical" : demandIndex >= 42 ? "high" : demandIndex >= 22 ? "elevated" : "baseline",
    windowHours: 6,
    demand,
    shortages,
    inventoryProvided: true,
    modelVersion: "scenario-planning-baseline-v1.0.0",
    modelKind: "transparent-deterministic-fallback",
    topSignals: [],
    environment: unavailableEnvironment,
    target: "resource demand during the next six-hour immediate-response window",
    confidenceLabel: "scenario baseline",
    providerCoverage: { available: 0, expected: 2, ratio: 0, sources: [], missing: ["Open-Meteo", "NASA POWER"] },
    provenance: { training: [], runtime: ["embedded scenario"] },
    planningBasis: {
      affectedPopulation: incident.affectedPopulation,
      quantityMethod: "risk index × hazard profile × affected population × disclosed category factor",
      labelType: "deterministic scenario baseline; neural service unavailable",
    },
    disclaimer: "Scenario-mode six-hour planning estimate. Quantities are modeled proxies, not verified needs or dispatch orders. Confirm with incident command and field assessments.",
  };
}

export function intelligenceFor(incident: Incident, resources: Resource[]) {
  return incident.intelligence?.demand?.length
    ? incident.intelligence
    : buildPlanningBaseline(incident, resources);
}
