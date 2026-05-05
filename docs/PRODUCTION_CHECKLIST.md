# Production checklist (before going live with a paying spa)

## Subprocessor BAAs
- [ ] OpenAI ZDR + BAA in place (or AI is OFF for this org)
- [ ] Twilio BAA signed
- [ ] Postgres host BAA (Supabase / Neon / RDS — pick one)
- [ ] Email provider BAA (Resend or SendGrid)

## Backend env
- [ ] `APP_ENV=production`
- [ ] `APP_SECRET_KEY` ≥32 random chars
- [ ] `DATABASE_URL` not localhost
- [ ] `CORS_ORIGINS` explicit, not `*`
- [ ] `TWILIO_VALIDATE_SIGNATURE=true`, `TWILIO_AUTH_TOKEN` set
- [ ] `OPENAI_LIVE=true` only with `OPENAI_API_KEY` set
- [ ] `LEMONSQUEEZY_SIGNING_SECRET` set, webhook URL configured in dashboard

## Billing
- [ ] LemonSqueezy store live, two variants created (Starter / Pro)
- [ ] Variant IDs copied to env
- [ ] Test-mode checkout end-to-end works locally

## Demo number
- [ ] `DEMO_TWILIO_NUMBER` provisioned and set
- [ ] Walkthrough completed end-to-end without errors

## Smoke test
- [ ] `docker-compose up --build`
- [ ] `alembic upgrade head` runs to head
- [ ] `python seed.py` creates demo orgs
- [ ] All curl examples in README succeed
- [ ] Login → dashboard → text demo number → reply appears in inbox
