import { AppShell } from "@/components/app-shell";
import { EvaluationDashboard } from "@/components/evaluation-dashboard";

export default function EvaluationsPage() {
  return (
    <AppShell>
      <main className="content evaluation-content">
        <EvaluationDashboard />
      </main>
    </AppShell>
  );
}
