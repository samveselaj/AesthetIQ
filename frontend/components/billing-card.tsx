"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Badge, Card, CardBody, CardHeader } from "@/components/ui";
import type { BillingStatus } from "@/types";

const PORTAL_URL = "https://app.lemonsqueezy.com/my-orders";

export function BillingCard() {
  const { data } = useQuery<BillingStatus>({
    queryKey: ["billing-status"],
    queryFn: () => api("/billing/status"),
  });
  const status = data?.subscription_status ?? "trialing";
  const tone =
    status === "active" || status === "trialing"
      ? "success"
      : status === "past_due"
      ? "warn"
      : "danger";
  return (
    <Card>
      <CardHeader>Billing</CardHeader>
      <CardBody className="flex items-center justify-between gap-4">
        <div>
          <div className="text-sm text-fg">
            Plan status: <Badge tone={tone}>{status}</Badge>
          </div>
          <p className="mt-1 text-xs text-muted">
            Billing handled by LemonSqueezy.
          </p>
        </div>
        <a
          className="text-sm underline hover:text-fg"
          href={PORTAL_URL}
          target="_blank"
          rel="noreferrer"
        >
          Manage subscription
        </a>
      </CardBody>
    </Card>
  );
}
