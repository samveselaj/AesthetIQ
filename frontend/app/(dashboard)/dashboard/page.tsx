"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardBody, PageHeader } from "@/components/ui";
import { AiToggle } from "@/components/ai-toggle";
import type { DashboardSummary } from "@/types";

export default function DashboardPage() {
  const { data, isLoading } = useQuery<DashboardSummary>({
    queryKey: ["dashboard-summary"],
    queryFn: () => api("/dashboard/summary"),
  });

  const stats: { label: string; value: string | number }[] = [
    { label: "Conversations handled (7d)", value: data?.conversations_handled_7d ?? "—" },
    { label: "Missed calls recovered (7d)", value: data?.missed_calls_recovered_7d ?? "—" },
    { label: "Booking links sent (7d)", value: data?.booking_links_sent_7d ?? "—" },
    { label: "Marked booked (7d)", value: data?.booked_7d ?? "—" },
    {
      label: "Avg first response",
      value: data?.avg_first_response_seconds
        ? `${Math.round(data.avg_first_response_seconds)}s`
        : "—",
    },
    {
      label: "AI handled without staff (7d)",
      value:
        data?.ai_handled_pct_7d !== null && data?.ai_handled_pct_7d !== undefined
          ? `${data.ai_handled_pct_7d}%`
          : "—",
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader title="Dashboard" description="Your week, at a glance." />
      <AiToggle />
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {stats.map((s) => (
          <Card key={s.label}>
            <CardBody>
              <div className="text-xs text-muted">{s.label}</div>
              <div className="mt-2 text-xl font-semibold text-fg">
                {isLoading ? "—" : s.value}
              </div>
            </CardBody>
          </Card>
        ))}
      </div>
    </div>
  );
}
