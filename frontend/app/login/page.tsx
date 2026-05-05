"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button, Card, CardBody, Field, Input } from "@/components/ui";
import { ThemeToggle } from "@/components/theme";
import { api, ApiError } from "@/lib/api";

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(1, "Password is required"),
});
type Form = z.infer<typeof schema>;

export default function LoginPage() {
  const router = useRouter();
  const [serverError, setServerError] = useState<string | null>(null);
  const [isDemoSubmitting, setIsDemoSubmitting] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Form>({
    resolver: zodResolver(schema),
    defaultValues: { email: "owner@glowaesthetics.demo", password: "demo1234" },
  });

  async function onSubmit(values: Form) {
    setServerError(null);
    try {
      await api("/auth/login", { method: "POST", json: values });
      router.replace("/dashboard");
    } catch (e) {
      setServerError(e instanceof ApiError ? e.message : "Something went wrong.");
    }
  }

  async function openDemoWorkspace() {
    setIsDemoSubmitting(true);
    try {
      await onSubmit({
        email: "owner@glowaesthetics.demo",
        password: "demo1234",
      });
    } finally {
      setIsDemoSubmitting(false);
    }
  }

  const isBusy = isSubmitting || isDemoSubmitting;

  return (
    <main className="min-h-screen">
      <header className="flex h-14 items-center justify-between border-b border-border px-4 sm:px-6">
        <span className="text-sm font-semibold text-fg">AesthetIQ</span>
        <ThemeToggle />
      </header>
      <div className="mx-auto flex w-full max-w-sm flex-col px-4 py-10">
        <h1 className="text-lg font-semibold text-fg">Sign in to the admin workspace</h1>
        <p className="mt-1 text-sm text-muted">
          Manage conversations, leads, FAQs, settings, and booking routes from one place.
        </p>
        <Card className="mt-6">
          <CardBody>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <Field label="Email" error={errors.email?.message}>
                <Input type="email" autoComplete="email" {...register("email")} />
              </Field>
              <Field label="Password" error={errors.password?.message}>
                <Input
                  type="password"
                  autoComplete="current-password"
                  {...register("password")}
                />
              </Field>
              {serverError && <p className="text-xs text-red-700 dark:text-red-400">{serverError}</p>}
              <Button type="submit" className="w-full" disabled={isBusy}>
                {isBusy ? "Signing in..." : "Sign in"}
              </Button>
              <Button
                type="button"
                variant="secondary"
                className="w-full"
                disabled={isBusy}
                onClick={openDemoWorkspace}
              >
                Open demo admin
              </Button>
            </form>
          </CardBody>
        </Card>
        <p className="mt-4 text-center text-xs text-muted">
          Demo credentials are filled in for local development.
        </p>
      </div>
    </main>
  );
}
