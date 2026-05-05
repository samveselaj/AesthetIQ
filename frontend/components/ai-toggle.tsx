"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardBody } from "@/components/ui";
import type { OrgSettings } from "@/types";

export function AiToggle() {
  const qc = useQueryClient();
  const { data } = useQuery<OrgSettings>({
    queryKey: ["settings"],
    queryFn: () => api("/settings"),
  });
  const mut = useMutation({
    mutationFn: (next: boolean) =>
      api("/settings", { method: "PATCH", json: { ai_enabled: next } }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["settings"] }),
  });
  if (!data) return null;
  const on = !!data.ai_enabled;
  return (
    <Card>
      <CardBody className="flex items-center justify-between gap-4">
        <div>
          <div className="text-sm font-medium text-fg">
            AI is {on ? "ON" : "OFF"}
          </div>
          <p className="mt-0.5 text-xs text-muted">
            {on
              ? "AI will auto-respond to inbound leads (rules + escalations still enforced)."
              : "All replies will be staged as drafts for staff review."}
          </p>
        </div>
        <button
          onClick={() => mut.mutate(!on)}
          disabled={mut.isPending}
          className={
            "inline-flex h-8 w-16 items-center rounded-full border border-border " +
            (on ? "bg-fg" : "bg-surface")
          }
          aria-pressed={on}
        >
          <span
            className={
              "size-6 rounded-full bg-bg transition-transform " +
              (on ? "translate-x-8" : "translate-x-1")
            }
          />
        </button>
      </CardBody>
    </Card>
  );
}
