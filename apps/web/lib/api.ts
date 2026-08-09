import { fallbackData } from "./fallback-data";
import type { DashboardData, Incident, Resource, Summary } from "./types";

const apiUrl = process.env.API_INTERNAL_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

async function getJSON<T>(path: string): Promise<T> {
  const response = await fetch(`${apiUrl}${path}`, { cache: "no-store", signal: AbortSignal.timeout(2500) });
  if (!response.ok) throw new Error(`${path} returned ${response.status}`);
  return response.json() as Promise<T>;
}

export async function getDashboardData(): Promise<DashboardData> {
  try {
    const [incidentResponse, resourceResponse, summary] = await Promise.all([
      getJSON<{ data: Incident[] }>("/api/v1/incidents?limit=100"),
      getJSON<{ data: Resource[] }>("/api/v1/resources"),
      getJSON<Summary>("/api/v1/summary"),
    ]);
    return {
      incidents: incidentResponse.data,
      resources: resourceResponse.data,
      summary,
      connected: true,
      streaming: true,
      dataMode: "operations",
    };
  } catch {
    return fallbackData;
  }
}
