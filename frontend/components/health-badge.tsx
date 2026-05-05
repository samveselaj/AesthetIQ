"use client";

import { useQuery } from "@tanstack/react-query";

type Health = {
  status: "ok" | "degraded";
  components: { twilio: string; openai: string };
};

const API =
  (typeof window === "undefined"
    ? process.env.INTERNAL_API_URL
    : process.env.NEXT_PUBLIC_API_URL) || "http://localhost:8000";

export function HealthBadge() {
  const { data } = useQuery<Health>({
    queryKey: ["health"],
    queryFn: async () => (await fetch(`${API}/health`)).json(),
    refetchInterval: 30_000,
  });
  const ok = data?.status === "ok";
  const label = !data
    ? "Checking…"
    : ok
    ? "All systems operational"
    : data.components.twilio !== "ok"
    ? "Twilio degraded"
    : "AI degraded";
  return (
    <div className="flex items-center gap-2 text-xs text-muted">
      <span
        className={
          "inline-block size-2 rounded-full " +
          (ok ? "bg-emerald-500" : "bg-amber-500")
        }
      />
      <span>{label}</span>
    </div>
  );
}
