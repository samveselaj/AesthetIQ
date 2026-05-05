"use client";

import { Monitor, Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

type Mode = "light" | "dark" | "system";

const order: Mode[] = ["light", "dark", "system"];
const icon = { light: Sun, dark: Moon, system: Monitor };
const label = { light: "Light", dark: "Dark", system: "System" };

function apply(mode: Mode) {
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const dark = mode === "dark" || (mode === "system" && prefersDark);
  document.documentElement.classList.toggle("dark", dark);
}

export function ThemeToggle({ className }: { className?: string }) {
  const [mode, setMode] = useState<Mode>("system");

  useEffect(() => {
    const stored = (localStorage.getItem("theme") as Mode | null) || "system";
    setMode(stored);
    apply(stored);
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const listener = () => {
      if ((localStorage.getItem("theme") as Mode | null) === "system") apply("system");
    };
    mq.addEventListener("change", listener);
    return () => mq.removeEventListener("change", listener);
  }, []);

  function cycle() {
    const next = order[(order.indexOf(mode) + 1) % order.length];
    setMode(next);
    localStorage.setItem("theme", next);
    apply(next);
  }

  const Icon = icon[mode];
  return (
    <button
      type="button"
      onClick={cycle}
      aria-label={`Theme: ${label[mode]} (click to change)`}
      className={cn(
        "inline-flex h-8 items-center gap-1.5 rounded-md border border-border bg-bg px-2 text-xs text-muted hover:bg-surface hover:text-fg",
        className
      )}
    >
      <Icon className="size-3.5" />
      <span>{label[mode]}</span>
    </button>
  );
}
