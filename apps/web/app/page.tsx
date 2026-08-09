import { CommandCenter } from "@/components/command-center";
import { getDashboardData } from "@/lib/api";

export default async function Home() {
  const data = await getDashboardData();
  return <CommandCenter initialData={data} />;
}

