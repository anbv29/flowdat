import { AppShell } from "@/components/app-shell";
import { QueryHistory } from "@/components/query-history";

export default function HistoryPage() {
  return <AppShell><main className="content"><QueryHistory /></main></AppShell>;
}
