import Link from "next/link";
import type { ReactNode } from "react";

const STARTER = process.env.NEXT_PUBLIC_LEMONSQUEEZY_CHECKOUT_STARTER || "#";
const PRO = process.env.NEXT_PUBLIC_LEMONSQUEEZY_CHECKOUT_PRO || "#";

function CheckoutLink({ href, children }: { href: string; children: ReactNode }) {
  const isConfigured = href !== "#";
  if (!isConfigured) {
    return (
      <span className="mt-6 inline-flex cursor-not-allowed items-center justify-center rounded-md border border-border px-4 py-2 text-sm font-medium text-muted">
        Checkout not configured
      </span>
    );
  }

  return (
    <a
      href={href}
      className="mt-6 inline-flex items-center justify-center rounded-md border border-border px-4 py-2 text-sm font-medium text-fg hover:bg-surface"
    >
      {children}
    </a>
  );
}

export default function PricingPage() {
  return (
    <main className="min-h-screen px-4 py-10 sm:px-6">
      <div className="mx-auto w-full max-w-4xl">
        <h1 className="text-2xl font-semibold text-fg">Simple pricing</h1>
        <p className="mt-2 text-sm text-muted">
          One US-based med spa. Cancel anytime. Billing in USD via LemonSqueezy.
        </p>
        <div className="mt-8 grid gap-4 md:grid-cols-2">
          <article className="rounded-md border border-border p-6">
            <h2 className="text-lg font-semibold text-fg">Starter</h2>
            <p className="mt-1 text-sm text-muted">
              1 location · SMS + missed-call recovery · up to 1,000 inbound msgs/mo
            </p>
            <p className="mt-4 text-3xl font-semibold text-fg">$297<span className="text-sm font-normal text-muted">/mo</span></p>
            <p className="text-xs text-muted">+ $497 setup</p>
            <CheckoutLink href={STARTER}>Start with Starter</CheckoutLink>
          </article>
          <article className="rounded-md border border-border p-6">
            <h2 className="text-lg font-semibold text-fg">Pro</h2>
            <p className="mt-1 text-sm text-muted">
              Everything in Starter + form webhook + follow-up sequences + priority support · up to 5,000 msgs/mo
            </p>
            <p className="mt-4 text-3xl font-semibold text-fg">$497<span className="text-sm font-normal text-muted">/mo</span></p>
            <p className="text-xs text-muted">+ $1,500 setup</p>
            <CheckoutLink href={PRO}>Start with Pro</CheckoutLink>
          </article>
        </div>
        <p className="mt-8 text-xs text-muted">
          <Link className="underline" href="/login">Back to sign in</Link>
        </p>
      </div>
    </main>
  );
}
