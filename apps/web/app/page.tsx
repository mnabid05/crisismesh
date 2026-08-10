import { PredictionDashboard } from "@/components/prediction-dashboard";
import { getDashboardData } from "@/lib/api";

export default async function Home() {
  const data = await getDashboardData();
  return <PredictionDashboard data={data} />;
}
