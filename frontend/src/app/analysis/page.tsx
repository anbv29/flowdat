import { Suspense } from "react";
import { AppShell } from "@/components/app-shell";
import { AnalysisWorkspace } from "@/components/analysis-workspace";

export default function AnalysisPage() {
  return (
    <AppShell>
      <Suspense fallback={<div className="analysis-loading">Preparing workspace…</div>}>
        <AnalysisWorkspace />
      </Suspense>
    </AppShell>
  );
}
