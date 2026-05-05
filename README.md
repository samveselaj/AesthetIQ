# MedSpaAISystem

AI-powered lead response and booking automation for medical spas.

This project is a production-minded MVP that helps med spas respond quickly to
new leads, answer common questions, route booking requests, and follow up
automatically while keeping staff in control.

## What It Does

- Captures inbound leads from SMS, missed calls, and website forms
- Uses deterministic safety rules before AI replies are sent
- Answers common questions from an approved FAQ knowledge base
- Sends the right booking link based on treatment and location
- Escalates sensitive or clinical messages to staff
- Tracks conversations, leads, booking activity, and AI handling in a dashboard
- Supports multi-tenant organizations with subscription gating

## Why It Matters

Med spas lose revenue when leads wait too long for a response. MedSpaAISystem is
designed to reduce response time, recover missed-call opportunities, and give
owners a practical automation layer without replacing human judgment.

## Tech Stack

- Frontend: Next.js, TypeScript, Tailwind CSS, TanStack Query
- Backend: FastAPI, SQLAlchemy, Alembic, Pydantic
- Database: PostgreSQL
- Background jobs: Redis and Celery
- AI: OpenAI with structured JSON responses and Pydantic validation
- Messaging: Twilio SMS and voice webhooks
- Billing: LemonSqueezy subscription webhooks
- Deployment: Docker Compose

## Local Setup

```bash
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local

docker-compose up --build
```

After the containers start:

```bash
docker-compose exec api alembic upgrade head
docker-compose exec api python seed.py
```

Local URLs:

- Web app: http://localhost:3000
- API docs: http://localhost:8000/docs

Demo login:

```text
email: owner@glowaesthetics.demo
password: demo1234
```

## Testing

```bash
cd backend && pytest -q
cd frontend && npm test
```

## Project Notes

This is not a CRM, EMR, or patient portal. A real healthcare deployment would
require HIPAA and vendor compliance review, including BAAs for relevant service
providers. See `docs/PRODUCTION_CHECKLIST.md` for production considerations.
