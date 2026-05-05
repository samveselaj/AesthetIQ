# AesthetIQ

**An AI concierge for medical spas.** Inbound leads (SMS, missed calls, web forms) are answered in seconds, qualified against an approved FAQ knowledge base, routed to the right booking link, and escalated to staff when the conversation crosses a clinical or sensitive line — all without giving the LLM the keys to the brand voice.

Production-minded MVP. Multi-tenant, subscription-gated, fully containerized, and engineered with the assumption that **the model can be wrong** — so deterministic rules, structured outputs, and human-in-the-loop overrides sit in front of every AI decision.

---

## Table of contents

- [The problem](#the-problem)
- [What AesthetIQ does](#what-aesthetiq-does)
- [Architecture](#architecture)
- [Engineering principles](#engineering-principles)
- [Tech stack](#tech-stack)
- [Quickstart](#quickstart)
- [Project layout](#project-layout)
- [Testing](#testing)
- [Deployment](#deployment)
- [Roadmap](#roadmap)
- [Compliance note](#compliance-note)

---

## The problem

Med spas convert leads on **response time**. A lead who pings a clinic at 9pm and waits until 10am the next morning is, statistically, gone. Most clinics don't staff a 24/7 front desk, and most generic chatbots are too risky for a setting where the wrong sentence becomes a medical claim, a pricing promise, or a HIPAA exposure.

AesthetIQ closes that gap with an AI agent that's deliberately narrow:

- It **only** answers from an FAQ block the clinic owner has approved.
- It **never** diagnoses, prices outside FAQs, or commits to outcomes.
- It hands every clinical/sensitive turn back to a human, automatically.

## What AesthetIQ does

- **Captures inbound leads** from Twilio SMS, missed-call webhooks, and website form posts.
- **Classifies intent and urgency** with a structured-output LLM call (intent, urgency, escalation flag, confidence).
- **Drafts replies grounded in approved FAQs** — refuses to answer if no FAQ confidently matches.
- **Routes booking links** by treatment + location (e.g. "Botox in Austin" → the Austin Botox booking page).
- **Escalates sensitive turns** (medical concerns, complaints, legal threats, pregnancy/treatment overlap) to staff via email.
- **Tracks every conversation, AI call, and decision** in an audit log surfaced through a Next.js dashboard.
- **Scopes everything to the org** with subscription gating (LemonSqueezy webhooks).

## Architecture

```
┌──────────────────┐      ┌─────────────────────┐      ┌──────────────────┐
│  Twilio SMS /    │ ───▶ │  FastAPI (api/v1)   │ ───▶ │  PostgreSQL      │
│  Web form        │      │                     │      │  (multi-tenant)  │
└──────────────────┘      │  ┌──────────────┐   │      └──────────────────┘
                          │  │ rules_engine │   │
                          │  │ phi_scrub    │   │      ┌──────────────────┐
                          │  │ ai_service   │ ◀─┼────▶ │  OpenAI          │
                          │  │ booking      │   │      │  (structured     │
                          │  │ escalation   │   │      │   JSON output)   │
                          │  └──────────────┘   │      └──────────────────┘
                          └──────┬──────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                  ▼
       ┌────────────┐     ┌────────────┐     ┌────────────┐
       │  Celery    │     │  Next.js   │     │  Twilio    │
       │  + Redis   │     │  dashboard │     │  outbound  │
       │  follow-up │     │  (Vercel)  │     │  SMS       │
       └────────────┘     └────────────┘     └────────────┘
```

**Request flow for an inbound message:**

1. Twilio webhook hits `/api/v1/webhooks/twilio`. Signature is validated against `TWILIO_AUTH_TOKEN` — unsigned requests are rejected.
2. Message is PHI-scrubbed before logging or being passed to OpenAI.
3. Deterministic rules engine runs first: business hours, blocked phrases, opt-out keywords. If a rule matches, we never call the LLM.
4. If we do call the LLM, the call is structured: classify → extract → draft, each step returning JSON validated by Pydantic. Failed validation = retry once, then escalate.
5. The drafted reply is gated by `should_escalate` and `should_send_booking_link` flags. Escalations go to staff email; booking-eligible turns get a routed link.
6. Outbound send goes through Twilio (or is logged-only when `TWILIO_LIVE=false`, which is how dev/CI/demo run).
7. Every step lands in `ai_log` and `audit_log` tables.

## Engineering principles

These are deliberate choices that surface in the code — recruiters reading this section, this is the part that matters.

- **Deterministic before stochastic.** A hard-coded `rules_engine` short-circuits the LLM for opt-outs, blocked phrases, and after-hours flows. The model only fires when rules don't already have an answer.
- **Grounded outputs only.** The system prompt forbids the model from answering with general knowledge. If no approved FAQ confidently matches, it must escalate or ask a clarifying question. Hallucination surface area is minimized at the prompt level, not patched downstream.
- **Structured JSON with Pydantic validation.** Every LLM call returns a typed object (`Classification`, `Extraction`, `Draft`). A response that fails schema validation is retried, then escalated — it never ships to the user as free text.
- **Versioned prompts.** `PROMPT_VERSION` is bumped when behavior changes, and stored on every `ai_log` row. Old replies stay traceable to the prompt that produced them.
- **Stub mode for every external dependency.** `OPENAI_LIVE`, `TWILIO_LIVE`, `EMAIL_LIVE` flags let CI, demos, and onboarding run end-to-end with zero external API costs. Health checks (`/health`) report the live/stub state per component.
- **Refuse-to-start config validation.** In production (`APP_ENV=production`) the app checks `APP_SECRET_KEY` length, CORS allowlist, Twilio signature validation, and a few other gotchas at boot. Misconfiguration crashes the process loudly instead of silently shipping insecure defaults. See [`Settings.validate_production`](backend/app/core/config.py).
- **Multi-tenant by default.** Every query is scoped by `organization_id`; subscription state gates the entire `/api/v1/*` surface except auth, onboarding, billing, and webhooks.
- **Same-origin frontend API calls.** The browser hits `/api/backend/*` (a Next.js rewrite to the FastAPI backend), so there is no CORS preflight in the hot path and the backend URL is never exposed to the client. See [`frontend/next.config.mjs`](frontend/next.config.mjs).
- **PHI scrubbing before logs.** Inbound message bodies are scrubbed before being persisted or sent to OpenAI. This is not a HIPAA-grade implementation — see [Compliance note](#compliance-note) — but the seam is in place.

## Tech stack

| Layer            | Choice                                                              |
| ---------------- | ------------------------------------------------------------------- |
| Frontend         | Next.js 16 (App Router, RSC), TypeScript, TanStack Query, Tailwind  |
| Backend          | FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, pydantic-settings    |
| Database         | PostgreSQL 15 (psycopg v3 driver)                                   |
| Background jobs  | Celery + Redis (scheduled follow-ups, async sends)                  |
| LLM              | OpenAI with JSON-mode + Pydantic validation                         |
| Messaging        | Twilio (SMS, voice webhooks, signature validation)                  |
| Email            | Resend or SendGrid (provider-agnostic)                              |
| Billing          | LemonSqueezy (Merchant of Record, webhook-driven subscription state)|
| Auth             | JWT in HttpOnly cookie (`medspa_session`), bcrypt-hashed passwords  |
| Deployment       | Docker Compose locally; Vercel (web) + Railway (api/db/redis) prod  |
| Tests            | pytest (backend), Vitest + Testing Library (frontend)               |

## Quickstart

**Prerequisites:** Docker, Node.js 20+, and either an OpenAI API key or stub mode.

```bash
git clone https://github.com/samveselaj/AesthetIQ.git
cd AesthetIQ

cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local

docker-compose up --build
```

Once the containers are healthy:

```bash
docker-compose exec api alembic upgrade head
docker-compose exec api python seed.py
```

Open the app:

| Service          | URL                              |
| ---------------- | -------------------------------- |
| Web app          | http://localhost:3000            |
| API (Swagger UI) | http://localhost:8000/docs       |
| API health       | http://localhost:8000/health     |

Demo login (created by `seed.py`):

```text
email:    owner@glowaesthetics.demo
password: demo1234
```

**Stub mode is on by default.** No OpenAI/Twilio calls go out until you flip `OPENAI_LIVE=true` / `TWILIO_LIVE=true` in `backend/.env` and provide real keys.

## Project layout

```
AesthetIQ/
├── backend/                    FastAPI service
│   ├── app/
│   │   ├── api/v1/             HTTP routes (auth, leads, ai, billing, webhooks…)
│   │   ├── core/               config, database, deps, security, logging
│   │   ├── models/             SQLAlchemy ORM (org, user, lead, conversation, ai_log…)
│   │   ├── prompts/            versioned LLM prompts + JSON schemas
│   │   ├── schemas/            Pydantic request/response/LLM-output schemas
│   │   ├── services/           ai_service, rules_engine, phi_scrub, booking,
│   │   │                       escalation, follow-up, twilio, billing…
│   │   └── workers/            Celery app and scheduled tasks
│   ├── alembic/                migrations
│   ├── tests/                  pytest suite
│   └── seed.py                 demo org/user/FAQ/booking-route fixtures
├── frontend/                   Next.js 16 web dashboard
│   ├── app/                    App Router pages (login, onboarding, dashboard…)
│   ├── components/             UI primitives + shell + theme + health badge
│   ├── lib/                    fetch wrapper, utils
│   └── tests/                  Vitest suite
├── docker-compose.yml          db, redis, api, worker, web
└── scripts/                    operational helpers
```

## Testing

```bash
# Backend
cd backend
pytest -q

# Frontend
cd frontend
npm test
```

Both suites run in stub mode and require no external services or secrets.

## Deployment

The reference deployment is **Vercel (web) + Railway (api + postgres + redis)**.

### Frontend → Vercel

- **Root Directory:** `frontend`
- **Node.js Version:** 20 or higher (enforced via `engines` in `package.json`)
- **Environment variables:**
  - `INTERNAL_API_URL` — the public URL of your Railway backend, **origin only** (e.g. `https://your-api.up.railway.app`). The Next.js rewrite appends `/api/v1/...` automatically — do **not** include a path or `:path*`.

### Backend → Railway

- **Service:** the `backend/` Dockerfile.
- **Add-ons:** Postgres + Redis (Railway plugins or Supabase/Upstash externals).
- **Environment variables:** copy from `backend/.env.example`. The app's `_normalize_db_url` rewrites Railway's auto-provisioned `postgresql://...` to `postgresql+psycopg://...` so the v3 driver is used — no extra config needed.
- **Start command** (already set by the Dockerfile): `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`.

### Webhook destinations

After the API is live:

- Twilio Messaging webhook → `https://<api>/api/v1/webhooks/twilio`
- LemonSqueezy webhook → `https://<api>/api/v1/webhooks/lemonsqueezy`

## Roadmap

Shipped:
- Inbound SMS + missed-call lead capture
- Rules-first LLM pipeline with structured JSON
- Escalation routing + audit log
- Multi-tenant onboarding with LemonSqueezy gating
- Stub mode for end-to-end dev without API keys

In progress / next:
- Voice transcription for missed-call follow-ups
- Per-clinic prompt overrides
- Analytics: response time, conversion, escalation rate
- Optional human-review-before-send mode

## Compliance note

This is a marketing/booking automation tool. **It is not a HIPAA-compliant medical record system, EMR, or patient portal.** A real healthcare deployment would require:

- A signed BAA with every covered service provider (OpenAI Enterprise, Twilio HIPAA, the email provider, the host)
- A formal risk assessment + breach response plan
- Stronger PHI handling than the included scrubber (encrypted-at-rest, field-level access controls, audit retention policy)
- Legal review of FAQ content and escalation thresholds

PHI scrubbing exists as a defense-in-depth seam, not as a compliance guarantee. Don't ship this to a covered entity without that work.

---

Built by [Sam Veselaj](https://github.com/samveselaj). Issues and PRs welcome.
