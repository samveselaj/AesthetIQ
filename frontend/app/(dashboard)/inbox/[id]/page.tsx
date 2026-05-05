"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import {
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  EmptyState,
  Select,
  Textarea,
} from "@/components/ui";
import type { ConversationDetail, Message } from "@/types";
import { cn, formatRelative } from "@/lib/utils";
import { ImproveReplyModal } from "@/components/improve-reply-modal";

function MessageRow({
  m,
  onImprove,
}: {
  m: Message;
  onImprove?: (id: string) => void;
}) {
  const inbound = m.direction === "inbound";
  return (
    <div
      className={cn(
        "flex w-full",
        inbound ? "justify-start" : "justify-end"
      )}
    >
      <div
        className={cn(
          "max-w-[85%] rounded-md border px-3 py-2 text-sm",
          inbound
            ? "border-border bg-surface text-fg"
            : "border-border bg-bg text-fg"
        )}
      >
        <div className="mb-0.5 text-[11px] text-muted">
          {m.sender_type}
          {m.ai_generated ? " · ai" : ""} · {formatRelative(m.created_at)}
        </div>
        <div className="whitespace-pre-wrap break-words">{m.content}</div>
        {m.ai_generated && onImprove && (
          <button
            onClick={() => onImprove(m.id)}
            className="mt-1 text-[11px] text-muted underline hover:text-fg"
          >
            Improve this reply
          </button>
        )}
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value?: string | null }) {
  return (
    <div className="flex items-start justify-between gap-3 text-sm">
      <dt className="text-muted">{label}</dt>
      <dd className="min-w-0 break-words text-right text-fg">{value || "—"}</dd>
    </div>
  );
}

export default function ConversationPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();

  const { data, isLoading } = useQuery<ConversationDetail>({
    queryKey: ["conversation", id],
    queryFn: () => api(`/conversations/${id}`),
    refetchInterval: 10_000,
  });

  const [reply, setReply] = useState("");
  const [improveId, setImproveId] = useState<string | null>(null);

  const sendReply = useMutation({
    mutationFn: () =>
      api(`/conversations/${id}/messages`, {
        method: "POST",
        json: { content: reply, channel_type: "sms" },
      }),
    onSuccess: () => {
      setReply("");
      qc.invalidateQueries({ queryKey: ["conversation", id] });
      qc.invalidateQueries({ queryKey: ["conversations"] });
    },
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["conversation", id] });
    qc.invalidateQueries({ queryKey: ["conversations"] });
  };

  const takeover = useMutation({
    mutationFn: () => api(`/conversations/${id}/takeover`, { method: "POST" }),
    onSuccess: invalidate,
  });
  const release = useMutation({
    mutationFn: () => api(`/conversations/${id}/release-ai`, { method: "POST" }),
    onSuccess: invalidate,
  });
  const markBooked = useMutation({
    mutationFn: () => api(`/conversations/${id}/mark-booked`, { method: "POST" }),
    onSuccess: invalidate,
  });
  const escalate = useMutation({
    mutationFn: (reason?: string) =>
      api(`/conversations/${id}/escalate`, {
        method: "POST",
        json: { reason: reason || null },
      }),
    onSuccess: invalidate,
  });
  const markLost = useMutation({
    mutationFn: (reason?: string) =>
      api(`/conversations/${id}/mark-lost`, {
        method: "POST",
        json: { reason: reason || null },
      }),
    onSuccess: invalidate,
  });
  const setBookingStatus = useMutation({
    mutationFn: (booking_status: string) =>
      api(`/leads/${data?.lead.id}`, {
        method: "PATCH",
        json: { booking_status },
      }),
    onSuccess: invalidate,
  });

  if (isLoading || !data)
    return <div className="text-sm text-muted">Loading…</div>;

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <div className="space-y-4 lg:col-span-2">
        <Card>
          <CardBody className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <h2 className="truncate text-base font-semibold text-fg">
                {data.lead.full_name || data.lead.first_name || data.lead.phone}
              </h2>
              <p className="mt-0.5 truncate text-xs text-muted">
                {data.lead.phone || data.lead.email || "No contact"} · {data.channel_type}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-1.5">
              {data.ai_mode === "escalated" ? (
                <Badge tone="danger">Escalated</Badge>
              ) : data.ai_mode === "paused" ? (
                <Badge tone="warn">Staff handling</Badge>
              ) : (
                <Badge tone="info">Auto-responding</Badge>
              )}
              {data.status === "closed" && (
                <Badge tone="neutral">Closed</Badge>
              )}
            </div>
          </CardBody>
        </Card>

        {data.ai_mode === "escalated" && (
          <div className="rounded-md border border-border bg-surface p-3 text-sm text-fg">
            This conversation is flagged for staff attention. Automated replies are paused until you release it.
          </div>
        )}

        <Card>
          <div className="flex max-h-[55vh] flex-col gap-2 overflow-y-auto p-4">
            {!data.messages.length ? (
              <EmptyState title="No messages yet" />
            ) : (
              data.messages.map((m) => (
                <MessageRow key={m.id} m={m} onImprove={setImproveId} />
              ))
            )}
          </div>
          <div className="border-t border-border p-3">
            <Textarea
              rows={2}
              placeholder="Type a reply…"
              value={reply}
              onChange={(e) => setReply(e.target.value)}
            />
            <div className="mt-2 flex flex-wrap items-center justify-end gap-2">
              {data.ai_mode !== "escalated" && data.status !== "closed" && (
                <Button
                  variant="danger"
                  size="sm"
                  onClick={() => {
                    const reason = window.prompt(
                      "Escalate to staff — why? (optional)"
                    );
                    if (reason !== null) escalate.mutate(reason);
                  }}
                  disabled={escalate.isPending}
                >
                  Escalate
                </Button>
              )}
              {data.status !== "closed" && (
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => {
                    if (
                      window.confirm(
                        "Mark this lead as lost? Pending follow-ups will be cancelled."
                      )
                    ) {
                      markLost.mutate(undefined);
                    }
                  }}
                  disabled={markLost.isPending}
                >
                  Mark lost
                </Button>
              )}
              <Button
                variant="secondary"
                size="sm"
                onClick={() => markBooked.mutate()}
                disabled={markBooked.isPending || data.status === "closed"}
              >
                Mark booked
              </Button>
              {data.ai_mode === "active" ? (
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => takeover.mutate()}
                  disabled={takeover.isPending}
                >
                  Pause auto-reply
                </Button>
              ) : (
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => release.mutate()}
                  disabled={release.isPending || data.status === "closed"}
                >
                  Resume auto-reply
                </Button>
              )}
              <Button
                size="sm"
                onClick={() => sendReply.mutate()}
                disabled={!reply.trim() || sendReply.isPending}
              >
                Send
              </Button>
            </div>
          </div>
        </Card>
      </div>

      <aside className="lg:col-span-1">
        <Card>
          <CardHeader>Lead</CardHeader>
          <CardBody>
            <dl className="space-y-2">
              <Row
                label="Name"
                value={data.lead.full_name || data.lead.first_name}
              />
              <Row label="Phone" value={data.lead.phone} />
              <Row label="Email" value={data.lead.email} />
              <Row label="Source" value={data.lead.source_type} />
              <Row label="Interest" value={data.lead.treatment_interest} />
              <Row label="Status" value={data.lead.status} />
              <div className="flex items-center justify-between gap-3 text-sm">
                <dt className="text-muted">Booking</dt>
                <dd className="min-w-0 flex-1 text-right">
                  <Select
                    value={data.lead.booking_status}
                    onChange={(e) => setBookingStatus.mutate(e.target.value)}
                    disabled={setBookingStatus.isPending}
                    className="ml-auto h-8 w-auto min-w-[9rem] text-xs"
                  >
                    <option value="not_sent">Not sent</option>
                    <option value="link_sent">Link sent</option>
                    <option value="booked">Booked</option>
                    <option value="declined">Declined</option>
                    <option value="unknown">Unknown</option>
                  </Select>
                </dd>
              </div>
            </dl>
          </CardBody>
        </Card>
      </aside>
      {improveId && (
        <ImproveReplyModal
          conversationId={id}
          messageId={improveId}
          onClose={() => setImproveId(null)}
        />
      )}
    </div>
  );
}
