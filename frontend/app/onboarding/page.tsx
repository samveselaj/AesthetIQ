"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import {
  Button,
  Card,
  CardBody,
  CardHeader,
  Field,
  Input,
  Textarea,
} from "@/components/ui";
import { ThemeToggle } from "@/components/theme";

type FAQDraft = { question: string; answer: string; category: string };
type RouteDraft = {
  treatment_name: string;
  normalized_treatment_key: string;
  booking_url: string;
};

export default function OnboardingPage() {
  const router = useRouter();
  const [serverError, setServerError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const params = new URLSearchParams(
    typeof window !== "undefined" ? window.location.search : ""
  );
  const token = params.get("token") || "";

  const [org, setOrg] = useState({
    org_name: "",
    org_slug: "",
    admin_name: "",
    admin_email: "",
    admin_password: "",
    location_name: "",
    location_timezone: "America/New_York",
    escalation_email: "",
  });

  const [faqs, setFaqs] = useState<FAQDraft[]>([
    { category: "pricing", question: "How much does Botox cost?", answer: "" },
  ]);
  const [routes, setRoutes] = useState<RouteDraft[]>([
    {
      treatment_name: "General consultation",
      normalized_treatment_key: "consultation_general",
      booking_url: "",
    },
  ]);

  async function submit() {
    setServerError(null);
    setSubmitting(true);
    try {
      const { escalation_email, ...rest } = org;
      await api(`/onboarding?token=${encodeURIComponent(token)}`, {
        method: "POST",
        json: {
          ...rest,
          ...(escalation_email ? { escalation_email } : {}),
          faqs: faqs.filter((f) => f.question && f.answer),
          booking_routes: routes.filter((r) => r.treatment_name),
        },
      });
      router.push("/login");
    } catch (e) {
      setServerError(e instanceof ApiError ? e.message : "Something went wrong");
    } finally {
      setSubmitting(false);
    }
  }

  if (!token) {
    return (
      <main className="min-h-screen flex items-center justify-center p-6">
        <p className="text-sm text-muted">
          This page needs a signup link from your purchase email. Check your inbox
          or visit <a href="/pricing" className="underline">/pricing</a>.
        </p>
      </main>
    );
  }

  return (
    <main className="min-h-screen">
      <header className="flex h-14 items-center justify-between border-b border-border px-4 sm:px-6">
        <span className="text-sm font-semibold text-fg">AesthetIQ</span>
        <ThemeToggle />
      </header>
      <div className="mx-auto w-full max-w-2xl px-4 py-8 sm:py-12">
        <h1 className="text-lg font-semibold text-fg">Create your workspace</h1>
        <p className="mt-1 text-sm text-muted">
          Takes about a minute. You can edit everything later.
        </p>

        <div className="mt-6 space-y-6">
          <Card>
            <CardHeader>Spa</CardHeader>
            <CardBody>
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Name">
                  <Input
                    value={org.org_name}
                    onChange={(e) => setOrg({ ...org, org_name: e.target.value })}
                  />
                </Field>
                <Field label="Slug">
                  <Input
                    value={org.org_slug}
                    onChange={(e) => setOrg({ ...org, org_slug: e.target.value })}
                    placeholder="glow-aesthetics"
                  />
                </Field>
              </div>
            </CardBody>
          </Card>

          <Card>
            <CardHeader>Primary location</CardHeader>
            <CardBody>
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Location name">
                  <Input
                    value={org.location_name}
                    onChange={(e) =>
                      setOrg({ ...org, location_name: e.target.value })
                    }
                  />
                </Field>
                <Field label="Timezone">
                  <Input
                    value={org.location_timezone}
                    onChange={(e) =>
                      setOrg({ ...org, location_timezone: e.target.value })
                    }
                  />
                </Field>
              </div>
            </CardBody>
          </Card>

          <Card>
            <CardHeader>Admin user</CardHeader>
            <CardBody>
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Your name">
                  <Input
                    value={org.admin_name}
                    onChange={(e) =>
                      setOrg({ ...org, admin_name: e.target.value })
                    }
                  />
                </Field>
                <Field label="Email">
                  <Input
                    type="email"
                    value={org.admin_email}
                    onChange={(e) =>
                      setOrg({ ...org, admin_email: e.target.value })
                    }
                  />
                </Field>
                <Field label="Password">
                  <Input
                    type="password"
                    value={org.admin_password}
                    onChange={(e) =>
                      setOrg({ ...org, admin_password: e.target.value })
                    }
                  />
                </Field>
                <Field label="Escalation email (optional)">
                  <Input
                    type="email"
                    value={org.escalation_email}
                    onChange={(e) =>
                      setOrg({ ...org, escalation_email: e.target.value })
                    }
                  />
                </Field>
              </div>
            </CardBody>
          </Card>

          <Card>
            <CardHeader>FAQs the AI may quote</CardHeader>
            <CardBody className="space-y-4">
              {faqs.map((f, i) => (
                <div key={i} className="space-y-3 border-b border-border pb-4 last:border-0 last:pb-0">
                  <div className="grid gap-3 sm:grid-cols-[1fr_2fr]">
                    <Field label="Category">
                      <Input
                        value={f.category}
                        onChange={(e) =>
                          setFaqs(
                            faqs.map((x, j) =>
                              j === i ? { ...x, category: e.target.value } : x
                            )
                          )
                        }
                      />
                    </Field>
                    <Field label="Question">
                      <Input
                        value={f.question}
                        onChange={(e) =>
                          setFaqs(
                            faqs.map((x, j) =>
                              j === i ? { ...x, question: e.target.value } : x
                            )
                          )
                        }
                      />
                    </Field>
                  </div>
                  <Field label="Answer">
                    <Textarea
                      rows={2}
                      value={f.answer}
                      onChange={(e) =>
                        setFaqs(
                          faqs.map((x, j) =>
                            j === i ? { ...x, answer: e.target.value } : x
                          )
                        )
                      }
                    />
                  </Field>
                </div>
              ))}
              <Button
                size="sm"
                variant="secondary"
                onClick={() =>
                  setFaqs([
                    ...faqs,
                    { category: "general", question: "", answer: "" },
                  ])
                }
              >
                Add FAQ
              </Button>
            </CardBody>
          </Card>

          <Card>
            <CardHeader>Booking routes</CardHeader>
            <CardBody className="space-y-4">
              {routes.map((r, i) => (
                <div
                  key={i}
                  className="grid gap-3 border-b border-border pb-4 last:border-0 last:pb-0 sm:grid-cols-2"
                >
                  <Field label="Treatment">
                    <Input
                      value={r.treatment_name}
                      onChange={(e) =>
                        setRoutes(
                          routes.map((x, j) =>
                            j === i
                              ? { ...x, treatment_name: e.target.value }
                              : x
                          )
                        )
                      }
                    />
                  </Field>
                  <Field label="Booking URL">
                    <Input
                      value={r.booking_url}
                      onChange={(e) =>
                        setRoutes(
                          routes.map((x, j) =>
                            j === i
                              ? { ...x, booking_url: e.target.value }
                              : x
                          )
                        )
                      }
                    />
                  </Field>
                </div>
              ))}
              <Button
                size="sm"
                variant="secondary"
                onClick={() =>
                  setRoutes([
                    ...routes,
                    {
                      treatment_name: "",
                      normalized_treatment_key: "",
                      booking_url: "",
                    },
                  ])
                }
              >
                Add route
              </Button>
            </CardBody>
          </Card>

          {serverError && (
            <p className="text-sm text-red-700 dark:text-red-400">
              {serverError}
            </p>
          )}

          <div className="flex justify-end">
            <Button onClick={submit} disabled={submitting}>
              {submitting ? "Creating…" : "Create workspace"}
            </Button>
          </div>
        </div>
      </div>
    </main>
  );
}
