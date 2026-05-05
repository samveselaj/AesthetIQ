"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Menu, X } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import type { Me } from "@/types";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "@/components/theme";
import { HealthBadge } from "@/components/health-badge";

const nav = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/inbox", label: "Inbox" },
  { href: "/leads", label: "Leads" },
  { href: "/faqs", label: "FAQs" },
  { href: "/settings", label: "Settings" },
];

function NavList({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  return (
    <nav className="flex flex-col">
      {nav.map((item) => {
        const active = pathname?.startsWith(item.href);
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            className={cn(
              "rounded-md px-3 py-2 text-sm transition-colors",
              active
                ? "bg-surface text-fg"
                : "text-muted hover:bg-surface hover:text-fg"
            )}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}

export function Shell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const {
    data: me,
    error,
    isLoading,
  } = useQuery<Me, ApiError>({
    queryKey: ["me"],
    queryFn: () => api<Me>("/auth/me"),
    retry: false,
  });

  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  useEffect(() => {
    if (error?.status === 401 || error?.status === 403) {
      router.replace("/login");
    }
  }, [error, router]);

  async function logout() {
    await api("/auth/logout", { method: "POST" });
    router.replace("/login");
  }

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center px-4">
        <div className="text-center">
          <div className="text-sm font-medium text-fg">Opening workspace</div>
          <div className="mt-1 text-xs text-muted">Checking your session...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center px-4">
        <div className="text-center">
          <div className="text-sm font-medium text-fg">Redirecting to sign in</div>
          <div className="mt-1 text-xs text-muted">Your session needs attention.</div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-56 flex-col border-r border-border bg-bg lg:flex">
        <div className="flex h-14 items-center border-b border-border px-4">
          <span className="text-sm font-semibold text-fg">AesthetIQ</span>
        </div>
        <div className="flex-1 overflow-y-auto p-3">
          <NavList />
        </div>
        <div className="border-t border-border p-3">
          <div className="mb-3">
            <HealthBadge />
          </div>
          <div className="mb-3 min-w-0">
            <div className="truncate text-sm text-fg">{me?.full_name ?? "—"}</div>
            <div className="truncate text-xs text-muted">{me?.email ?? ""}</div>
          </div>
          <div className="flex items-center justify-between gap-2">
            <ThemeToggle />
            <button
              onClick={logout}
              className="text-xs text-muted hover:text-fg"
            >
              Log out
            </button>
          </div>
        </div>
      </aside>

      {/* Mobile top bar */}
      <header className="sticky top-0 z-10 flex h-14 items-center justify-between border-b border-border bg-bg px-4 lg:hidden">
        <span className="text-sm font-semibold text-fg">AesthetIQ</span>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <button
            onClick={() => setOpen(true)}
            aria-label="Open menu"
            className="rounded-md p-1.5 text-muted hover:bg-surface hover:text-fg"
          >
            <Menu className="size-5" />
          </button>
        </div>
      </header>

      {/* Mobile drawer */}
      {open && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-30 lg:hidden"
        >
          <button
            aria-label="Close menu"
            onClick={() => setOpen(false)}
            className="absolute inset-0 bg-black/40"
          />
          <div className="absolute inset-y-0 left-0 flex w-72 max-w-[85%] flex-col border-r border-border bg-bg">
            <div className="flex h-14 items-center justify-between border-b border-border px-4">
              <span className="text-sm font-semibold text-fg">
                AesthetIQ
              </span>
              <button
                onClick={() => setOpen(false)}
                aria-label="Close"
                className="rounded-md p-1.5 text-muted hover:bg-surface hover:text-fg"
              >
                <X className="size-5" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-3">
              <NavList onNavigate={() => setOpen(false)} />
            </div>
            <div className="border-t border-border p-3">
              <div className="mb-3">
                <HealthBadge />
              </div>
              <div className="mb-3 min-w-0">
                <div className="truncate text-sm text-fg">
                  {me?.full_name ?? "—"}
                </div>
                <div className="truncate text-xs text-muted">
                  {me?.email ?? ""}
                </div>
              </div>
              <button
                onClick={logout}
                className="text-xs text-muted hover:text-fg"
              >
                Log out
              </button>
            </div>
          </div>
        </div>
      )}

      <main className="lg:pl-56">
        <div className="mx-auto w-full max-w-5xl px-4 py-6 sm:px-6 sm:py-8">
          {children}
        </div>
      </main>
    </div>
  );
}
