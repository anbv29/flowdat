import { AppShell } from "@/components/app-shell";

export default function Home() {
  return (
    <AppShell>
      <main className="content">
        <p className="eyebrow">Workspace</p>
        <h1>Your datasets</h1>
        <p className="lede">Keep source files, profiles, and analysis together in one quiet workspace.</p>
      </main>
    </AppShell>
  );
}
