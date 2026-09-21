import { AppShell } from "@/components/app-shell";
import { DatasetOverview } from "@/components/dataset-overview";

export default function DatasetPage() {
  return (
    <AppShell>
      <main className="content dataset-content">
        <DatasetOverview />
      </main>
    </AppShell>
  );
}
