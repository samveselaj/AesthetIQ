"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api";
import { Badge, Card, EmptyState, PageHeader } from "@/components/ui";
import type { ConversationListItem, Page } from "@/types";
import { formatRelative } from "@/lib/utils";

function StatusBadge({ item }: { item: ConversationListItem }) {
  if (item.escalation_state === "escalated")
    return <Badge tone="danger">Escalated</Badge>;
  if (item.status === "waiting_on_staff")
    return <Badge tone="warn">Needs reply</Badge>;
  if (item.status === "waiting_on_lead")
    return <Badge tone="info">Waiting</Badge>;
  if (item.status === "closed") return <Badge>Closed</Badge>;
  return <Badge tone="success">Open</Badge>;
}

export default function InboxPage() {
  const { data, isLoading } = useQuery<Page<ConversationListItem>>({
    queryKey: ["conversations"],
    queryFn: () => api("/conversations?limit=100"),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Inbox"
        description="Inbound conversations across SMS, forms, and missed calls."
      />
      <Card className="overflow-hidden">
        {isLoading ? (
          <div className="p-6 text-sm text-muted">Loading…</div>
        ) : !data?.items.length ? (
          <EmptyState
            title="No conversations yet"
            description="Inbound SMS, form submissions, and missed calls will show up here."
          />
        ) : (
          <ul className="divide-y divide-border">
            {data.items.map((c) => (
              <li key={c.id}>
                <Link
                  href={`/inbox/${c.id}`}
                  className="flex items-start gap-3 px-4 py-3 hover:bg-surface"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="truncate text-sm font-medium text-fg">
                        {c.lead_name || c.lead_phone || "Unknown lead"}
                      </span>
                      <StatusBadge item={c} />
                    </div>
                    <p className="mt-1 break-words text-xs text-muted line-clamp-2">
                      {c.last_message_preview || "—"}
                    </p>
                  </div>
                  <div className="shrink-0 whitespace-nowrap text-xs text-muted">
                    {formatRelative(c.last_message_at)}
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
