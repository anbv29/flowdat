import { BarChart3, Database, History, PanelLeft, Sparkles } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";

const navigation = [
  { label: "Datasets", href: "/", icon: Database, active: true },
  { label: "Analysis", href: "/analysis", icon: Sparkles },
  { label: "History", href: "/history", icon: History },
  { label: "Evaluations", href: "/evaluations", icon: BarChart3 },
];

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="app-frame">
      <aside className="sidebar" aria-label="Primary navigation">
        <Link className="brand" href="/" aria-label="SignalDesk home">
          <span className="brand-mark" aria-hidden="true">
            <i />
            <i />
            <i />
          </span>
          <span>SignalDesk</span>
        </Link>

        <nav className="nav-list">
          {navigation.map(({ label, href, icon: Icon, active }) => (
            <Link className={active ? "nav-item is-active" : "nav-item"} href={href} key={label}>
              <Icon size={17} strokeWidth={1.8} />
              <span>{label}</span>
            </Link>
          ))}
        </nav>

        <div className="sidebar-note">
          <span className="status-dot" />
          <div>
            <strong>Local workspace</strong>
            <p>Your files stay on this machine.</p>
          </div>
        </div>
      </aside>

      <div className="main-column">
        <header className="topbar">
          <Button className="mobile-menu" variant="ghost" size="small" aria-label="Open navigation">
            <PanelLeft size={18} />
          </Button>
          <span className="workspace-name">Personal workspace</span>
          <div className="avatar" aria-label="Current user">
            AP
          </div>
        </header>
        {children}
      </div>
    </div>
  );
}
