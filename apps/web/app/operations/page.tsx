import { OperationsBoard } from "@/components/operations-board";
import { getDashboardData } from "@/lib/api";

export default async function OperationsPage() {
  return <OperationsBoard data={await getDashboardData()} />;
}
