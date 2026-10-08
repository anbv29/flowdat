"use client";

import { BarChart3, Database, History, PanelLeft } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, type ReactNode } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { Button } from "@/components/ui/button";

const navigation = [
  { label: "Datasets", href: "/", icon: Database },
  { label: "History", href: "/history", icon: History },
  { label: "Evaluations", href: "/evaluations", icon: BarChart3 },
];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
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
          {navigation.map(({ label, href, icon: Icon }) => {
            const active = href === "/" ? pathname === "/" || pathname.startsWith("/datasets/") : pathname.startsWith(href);
            return (
            <Link className={active ? "nav-item is-active" : "nav-item"} href={href} key={label}>
              <Icon size={17} strokeWidth={1.8} />
              <span>{label}</span>
            </Link>
          );})}
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
          <Button className="mobile-menu" variant="ghost" size="small" aria-label="Open navigation" onClick={() => setMenuOpen(true)}>
            <PanelLeft size={18} />
          </Button>
          <span className="workspace-name">Personal workspace</span>
          <div className="avatar" aria-label="Current user">
            AP
          </div>
        </header>
        {children}
        <Dialog.Root open={menuOpen} onOpenChange={setMenuOpen}>
          <Dialog.Portal>
            <Dialog.Overlay className="dialog-overlay" />
            <Dialog.Content className="navigation-drawer">
              <Dialog.Title>SignalDesk</Dialog.Title>
              <Dialog.Description>Navigate your workspace.</Dialog.Description>
              <nav aria-label="Mobile navigation">
                {navigation.map(({ label, href, icon: Icon }) => (
                  <Link href={href} key={href} onClick={() => setMenuOpen(false)} className="nav-item">
                    <Icon size={18} /><span>{label}</span>
                  </Link>
                ))}
              </nav>
              <Dialog.Close asChild><Button variant="secondary">Close navigation</Button></Dialog.Close>
            </Dialog.Content>
          </Dialog.Portal>
        </Dialog.Root>
      </div>
    </div>
  );
}
