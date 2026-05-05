"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import {
  Button,
  Card,
  CardBody,
  CardHeader,
  Field,
  Input,
  PageHeader,
  Textarea,
} from "@/components/ui";
import { BillingCard } from "@/components/billing-card";
import type { OrgSettings } from "@/types";

function Checkbox({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="flex cursor-pointer items-center gap-2 text-sm">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="size-4 rounded border-border accent-fg"
      />
      <span className="text-fg">{label}</span>
    </label>
  );
}

export default function SettingsPage() {
  const qc = useQueryClient();
  const { data } = useQuery<OrgSettings>({
    queryKey: ["settings"],
    queryFn: () => api("/settings"),
  });

  const [form, setForm] = useState<Partial<OrgSettings> | null>(null);
  useEffect(() => {
    if (data) setForm(data);
  }, [data]);

  const save = useMutation({
    mutationFn: () => api("/settings", { method: "PATCH", json: form }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["settings"] }),
  });

  if (!form) return <div className="text-sm text-muted">Loading…</div>;

  return (
    <div className="max-w-3xl space-y-6">
      <PageHeader
        title="Settings"
        description="Branding, tone, disclaimers, and auto-reply behavior."
      />
      <Card>
        <CardHeader>Workspace</CardHeader>
        <CardBody className="space-y-4">
          <Field label="Brand name">
            <Input
              value={form.brand_name ?? ""}
              onChange={(e) => setForm({ ...form, brand_name: e.target.value })}
            />
          </Field>
          <Field label="Tone of voice">
            <Textarea
              rows={3}
              value={form.tone_of_voice ?? ""}
              onChange={(e) =>
                setForm({ ...form, tone_of_voice: e.target.value })
              }
            />
          </Field>
          <Field
            label="Disclaimers"
            hint="Healthcare deployments may require additional compliance review."
          >
            <Textarea
              rows={3}
              value={form.disclaimers ?? ""}
              onChange={(e) => setForm({ ...form, disclaimers: e.target.value })}
            />
          </Field>
          <Field label="Escalation holding message">
            <Textarea
              rows={2}
              value={form.escalation_message ?? ""}
              onChange={(e) =>
                setForm({ ...form, escalation_message: e.target.value })
              }
            />
          </Field>
          <div className="grid gap-3 sm:grid-cols-2">
            <Checkbox
              label="Auto-reply enabled"
              checked={!!form.ai_enabled}
              onChange={(v) => setForm({ ...form, ai_enabled: v })}
            />
            <Checkbox
              label="Send replies automatically"
              checked={!!form.auto_send_replies}
              onChange={(v) => setForm({ ...form, auto_send_replies: v })}
            />
          </div>
          <div className="flex justify-end pt-1">
            <Button onClick={() => save.mutate()} disabled={save.isPending}>
              Save changes
            </Button>
          </div>
        </CardBody>
      </Card>
      <BillingCard />
    </div>
  );
}
