"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import { Card, CardBody, CardHeader, PageHeader } from "@/components/ui";
import type { Lead } from "@/types";

function Row({ label, value }: { label: string; value?: string | null }) {
  return (
    <div className="flex items-start justify-between gap-3 text-sm">
      <dt className="text-muted">{label}</dt>
      <dd className="min-w-0 break-words text-right text-fg">{value || "—"}</dd>
    </div>
  );
}

export default function LeadDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data, isLoading } = useQuery<Lead>({
    queryKey: ["lead", id],
    queryFn: () => api(`/leads/${id}`),
  });

  if (isLoading || !data)
    return <div className="text-sm text-muted">Loading…</div>;

  const subtitle = [data.source_type, data.source_label]
    .filter(Boolean)
    .join(" · ");

  return (
    <div className="space-y-6">
      <PageHeader
        title={data.full_name || data.first_name || "Lead"}
        description={subtitle}
      />
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>Contact</CardHeader>
          <CardBody>
            <dl className="space-y-2">
              <Row label="Phone" value={data.phone} />
              <Row label="Email" value={data.email} />
              <Row label="Interest" value={data.treatment_interest} />
            </dl>
          </CardBody>
        </Card>
        <Card>
          <CardHeader>Lifecycle</CardHeader>
          <CardBody>
            <dl className="space-y-2">
              <Row label="Status" value={data.status} />
              <Row label="Stage" value={data.lifecycle_stage} />
              <Row label="Booking" value={data.booking_status} />
              <Row
                label="Do not contact"
                value={data.do_not_contact ? "yes" : "no"}
              />
            </dl>
          </CardBody>
        </Card>
      </div>
      {data.notes && (
        <Card>
          <CardHeader>Notes</CardHeader>
          <CardBody>
            <p className="whitespace-pre-wrap break-words text-sm text-muted">
              {data.notes}
            </p>
          </CardBody>
        </Card>
      )}
    </div>
  );
}
