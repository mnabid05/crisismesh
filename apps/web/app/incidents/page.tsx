import { IncidentCatalog } from "@/components/incident-catalog";
import { getDashboardData } from "@/lib/api";

export default async function IncidentsPage() {
  return <IncidentCatalog data={await getDashboardData()} />;
}
