"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import {
  GitCompareArrows,
  FileText,
  LayoutDashboard,
  LogOut,
  Menu,
  MessagesSquare,
  Settings,
  ShieldCheck,
  X,
} from "lucide-react";

import { useAuth } from "@/lib/auth";
import { initials } from "@/lib/format";
import { cn } from "./ui";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/documents", label: "Documents", icon: FileText },
  { href: "/chat", label: "AI chat", icon: MessagesSquare },
  { href: "/compare", label: "Compare", icon: GitCompareArrows },
  { href: "/settings", label: "Settings", icon: Settings },
];

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  return (
    <nav className="space-y-1" aria-label="Main">
      {NAV.map((item) => {
        const active =
          pathname === item.href || pathname.startsWith(`${item.href}/`);
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            aria-current={active ? "page" : undefined}
            className={cn(
              "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
              active
                ? "bg-primary/10 text-primary"
                : "text-muted-foreground hover:bg-muted hover:text-foreground",
            )}
          >
            <item.icon size={17} aria-hidden />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}

function UserCard() {
  const { user, signOut } = useAuth();
  if (!user) return null;
  return (
    <div className="rounded-lg border border-border bg-background p-2.5">
      <div className="flex items-center gap-2.5">
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
          {initials(user.full_name, user.email)}
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-xs font-medium text-foreground">
            {user.full_name || "Your account"}
          </p>
          <p className="truncate text-[11px] text-muted-foreground">{user.email}</p>
        </div>
        <button
          type="button"
          onClick={() => void signOut()}
          className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          aria-label="Sign out"
          title="Sign out"
        >
          <LogOut size={15} aria-hidden />
        </button>
      </div>
    </div>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="min-h-dvh bg-background">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 flex-col border-r border-border bg-white px-3 py-4 lg:flex">
        <Link href="/dashboard" className="mb-6 flex items-center gap-2 px-2 font-semibold">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <ShieldCheck size={18} aria-hidden />
          </span>
          <span className="tracking-tight">Insurio</span>
        </Link>
        <div className="flex-1">
          <NavLinks />
        </div>
        <div className="space-y-3">
          <Link
            href="/documents"
            className="block rounded-lg border border-dashed border-border px-3 py-2.5 text-xs text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground"
          >
            <span className="font-medium text-foreground">Upload a policy</span>
            <br />
            PDF, up to 20 MB
          </Link>
          <UserCard />
        </div>
      </aside>

      {open ? (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            type="button"
            aria-label="Close navigation"
            className="absolute inset-0 bg-foreground/30"
            onClick={() => setOpen(false)}
          />
          <div className="relative flex h-full w-72 flex-col border-r border-border bg-white px-3 py-4 shadow-lift">
            <div className="mb-6 flex items-center justify-between px-2">
              <Link href="/dashboard" className="flex items-center gap-2 font-semibold">
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                  <ShieldCheck size={18} aria-hidden />
                </span>
                Insurio
              </Link>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="rounded-md p-1.5 text-muted-foreground hover:bg-muted"
                aria-label="Close menu"
              >
                <X size={18} aria-hidden />
              </button>
            </div>
            <div className="flex-1">
              <NavLinks onNavigate={() => setOpen(false)} />
            </div>
            <UserCard />
          </div>
        </div>
      ) : null}

      <div className="lg:pl-64">
        <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-border bg-background/85 px-4 backdrop-blur lg:hidden">
          <button
            type="button"
            onClick={() => setOpen(true)}
            className="rounded-md p-2 text-muted-foreground hover:bg-muted"
            aria-label="Open navigation"
            aria-expanded={open}
          >
            <Menu size={19} aria-hidden />
          </button>
          <Link href="/dashboard" className="flex items-center gap-2 text-sm font-semibold">
            <ShieldCheck size={17} className="text-primary" aria-hidden />
            Insurio
          </Link>
          <span className="w-9" aria-hidden />
        </header>
        <main className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          {children}
        </main>
      </div>
    </div>
  );
}
