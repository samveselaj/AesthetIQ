"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api";
import { Badge, Card, EmptyState, PageHeader } from "@/components/ui";
import type { Lead, Page } from "@/types";
import { formatRelative } from "@/lib/utils";

const toneByStatus: Record<string, Parameters<typeof Badge>[0]["tone"]> = {
  new: "info",
  contacted: "neutral",
  qualified: "neutral",
  booked: "success",
  escalated: "danger",
  closed_lost: "neutral",
  no_response: "warn",
};

export default function LeadsPage() {
  const { data, isLoading } = useQuery<Page<Lead>>({
    queryKey: ["leads"],
    queryFn: () => api("/leads?limit=200"),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Leads"
        description="Everyone who's reached out — source, status, and interest."
      />
      <Card className="overflow-hidden">
        {isLoading ? (
          <div className="p-6 text-sm text-muted">Loading…</div>
        ) : !data?.items.length ? (
          <EmptyState title="No leads yet" />
        ) : (
          <>
            {/* Desktop */}
            <div className="hidden md:block">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-surface text-xs text-muted">
                    <tr>
                      <th className="px-4 py-2.5 text-left font-medium">Name</th>
                      <th className="px-4 py-2.5 text-left font-medium">Phone</th>
                      <th className="px-4 py-2.5 text-left font-medium">Email</th>
                      <th className="px-4 py-2.5 text-left font-medium">Source</th>
                      <th className="px-4 py-2.5 text-left font-medium">Interest</th>
                      <th className="px-4 py-2.5 text-left font-medium">Status</th>
                      <th className="px-4 py-2.5 text-left font-medium">Created</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {data.items.map((l) => (
                      <tr key={l.id} className="hover:bg-surface">
                        <td className="px-4 py-2.5">
                          <Link
                            href={`/leads/${l.id}`}
                            className="font-medium text-fg hover:underline"
                          >
                            {l.full_name || l.first_name || "—"}
                          </Link>
                        </td>
                        <td className="px-4 py-2.5 text-muted">
                          {l.phone || "—"}
                        </td>
                        <td className="px-4 py-2.5 text-muted">
                          {l.email || "—"}
                        </td>
                        <td className="px-4 py-2.5 text-muted">
                          {l.source_type}
                        </td>
                        <td className="px-4 py-2.5 text-muted">
                          {l.treatment_interest || "—"}
                        </td>
                        <td className="px-4 py-2.5">
                          <Badge tone={toneByStatus[l.status] || "neutral"}>
                            {l.status.replace("_", " ")}
                          </Badge>
                        </td>
                        <td className="px-4 py-2.5 text-muted">
                          {formatRelative(l.created_at)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Mobile */}
            <ul className="divide-y divide-border md:hidden">
              {data.items.map((l) => (
                <li key={l.id}>
                  <Link
                    href={`/leads/${l.id}`}
                    className="flex flex-col gap-1 px-4 py-3 hover:bg-surface"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate text-sm font-medium text-fg">
                        {l.full_name || l.first_name || "—"}
                      </span>
                      <Badge tone={toneByStatus[l.status] || "neutral"}>
                        {l.status.replace("_", " ")}
                      </Badge>
                    </div>
                    <div className="truncate text-xs text-muted">
                      {l.phone || l.email || "—"} · {l.source_type}
                      {l.treatment_interest ? ` · ${l.treatment_interest}` : ""}
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          </>
        )}
      </Card>
    </div>
  );
}
