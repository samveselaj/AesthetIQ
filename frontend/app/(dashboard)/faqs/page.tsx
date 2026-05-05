"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api";
import {
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  EmptyState,
  Field,
  Input,
  PageHeader,
  Textarea,
} from "@/components/ui";
import type { FAQ } from "@/types";

export default function FaqsPage() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery<FAQ[]>({
    queryKey: ["faqs"],
    queryFn: () => api("/faqs"),
  });

  const [form, setForm] = useState({
    category: "general",
    question: "",
    answer: "",
  });

  const create = useMutation({
    mutationFn: () =>
      api("/faqs", {
        method: "POST",
        json: { ...form, is_active: true, priority: 100 },
      }),
    onSuccess: () => {
      setForm({ category: "general", question: "", answer: "" });
      qc.invalidateQueries({ queryKey: ["faqs"] });
    },
  });

  const toggle = useMutation({
    mutationFn: (f: FAQ) =>
      api(`/faqs/${f.id}`, {
        method: "PATCH",
        json: { is_active: !f.is_active },
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["faqs"] }),
  });

  const del = useMutation({
    mutationFn: (id: string) => api(`/faqs/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["faqs"] }),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Knowledge"
        description="Approved answers the AI is allowed to quote from."
      />

      <Card>
        <CardHeader>Add FAQ</CardHeader>
        <CardBody className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-4">
            <Field label="Category">
              <Input
                value={form.category}
                onChange={(e) => setForm({ ...form, category: e.target.value })}
              />
            </Field>
            <div className="sm:col-span-3">
              <Field label="Question">
                <Input
                  value={form.question}
                  onChange={(e) =>
                    setForm({ ...form, question: e.target.value })
                  }
                />
              </Field>
            </div>
          </div>
          <Field label="Answer">
            <Textarea
              rows={3}
              value={form.answer}
              onChange={(e) => setForm({ ...form, answer: e.target.value })}
            />
          </Field>
          <div className="flex justify-end">
            <Button
              size="sm"
              onClick={() => create.mutate()}
              disabled={
                !form.question.trim() ||
                !form.answer.trim() ||
                create.isPending
              }
            >
              Add
            </Button>
          </div>
        </CardBody>
      </Card>

      <Card className="overflow-hidden">
        {isLoading ? (
          <div className="p-6 text-sm text-muted">Loading…</div>
        ) : !data?.length ? (
          <EmptyState
            title="No FAQs yet"
            description="Add the questions your team answers every day."
          />
        ) : (
          <ul className="divide-y divide-border">
            {data.map((f) => (
              <li key={f.id} className="px-4 py-3">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <Badge>{f.category}</Badge>
                      {!f.is_active && <Badge tone="warn">inactive</Badge>}
                    </div>
                    <div className="mt-1.5 break-words text-sm font-medium text-fg">
                      {f.question}
                    </div>
                    <p className="mt-1 whitespace-pre-wrap break-words text-sm text-muted">
                      {f.answer}
                    </p>
                  </div>
                  <div className="flex shrink-0 gap-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => toggle.mutate(f)}
                    >
                      {f.is_active ? "Disable" : "Enable"}
                    </Button>
                    <Button
                      variant="danger"
                      size="sm"
                      onClick={() => del.mutate(f.id)}
                    >
                      Delete
                    </Button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
