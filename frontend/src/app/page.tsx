import { AppShell } from "@/components/app-shell";
import { DatasetLibrary } from "@/components/dataset-library";

export default function Home() {
  return (
    <AppShell>
      <main className="content">
        <DatasetLibrary />
      </main>
    </AppShell>
  );
}
