# SELLING.md — internal sales notes

## Elevator pitch

Reply to every med spa lead in under 60 seconds — 24/7. We catch missed calls,
answer pricing questions, and send the booking link before your competitor does.
The AI handles repetitive Botox/filler/laser pricing texts, recovers missed
calls automatically, and escalates anything medical to your team. The owner
sees one dashboard tile that matters: *AI handled without staff (7d)*.

## Demo script

Live walkthrough: `scripts/demo_walkthrough.md`. Targets ≈90 seconds, recorded
with Loom. Pre-set: empty inbox, AI on, browser at `/inbox`. Cover: Botox
pricing reply, STOP opt-out, medical escalation, Improve-this-reply correction
loop, and the dashboard's `AI handled without staff (7d)` ≥ 80%.

## Objection handling

### "Are you HIPAA-compliant?"

Not a HIPAA-covered service yet. Before any production deployment in a clinical
setting we sign BAAs with all subprocessors (Twilio, OpenAI, Postgres host,
email provider). The AI side runs on OpenAI with ZDR + no-train guarantees.
In-flight payloads are scrubbed of likely-PHI keys (`ssn`, `dob`,
`date_of_birth`, `insurance`, `medical_record`, `mrn`) before persistence.
Production env startup gates refuse to boot without Twilio signature
validation, explicit CORS, and a real `APP_SECRET_KEY`. See
`docs/PRODUCTION_CHECKLIST.md`.

### "Do you integrate with Boulevard / Mindbody / Vagaro / Mangomint?"

Not directly. We send the booking URL you already have — same link your front
desk emails today. Direct integrations are on the roadmap once we have ten
paying spas asking for the same one. Building integration #1 against
Boulevard alone would burn the runway it takes to land paying customers #2
through #10.

### "What if the AI says something wrong?"

Three layers:
1. The rules engine pre-empts AI on STOP, medical/complaint keywords, and
   off-hours — those go straight to a holding reply + escalation, no LLM call.
2. AI output is Pydantic-validated; an unparseable response is treated as
   "uncertain" and escalates by default.
3. The Improve-this-reply loop in `/inbox/[id]` lets staff promote a corrected
   answer to a high-priority FAQ entry inside an hour. Next time a similar
   inbound arrives, the corrected FAQ is preferred.

If a customer is still uncomfortable: the dashboard has a one-click
`AI is OFF` toggle that demotes every reply to a staff draft.

## Pricing rationale

- **Starter — $297/mo + $497 setup.** One location. SMS + missed-call
  recovery. Up to 1,000 inbound msgs/mo. Pays for the Twilio number,
  Postgres/Redis allocation, and OpenAI usage at expected pricing-question
  volume for a single-location spa.
- **Pro — $497/mo + $1,500 setup.** Adds the website-form webhook and
  multi-step follow-up sequences. Up to 5,000 inbound msgs/mo. Pro covers
  spas with paid ad funnels and 2+ inbound channels.

The setup fees fund white-glove onboarding — we still hand-build their first
10 FAQs and 5 booking routes. Once 10 customers are live, those become
templated.

LemonSqueezy is Merchant of Record (we're based in Kosovo; Stripe will not
onboard sellers from Kosovo). LMS handles US sales tax + chargebacks. Net
revenue is roughly 95% after their fee.
