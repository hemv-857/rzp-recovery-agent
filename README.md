# Razorpay Revenue Recovery Agent

**Track 03 — AI Revenue Recovery.** An agent that closes the loop from detecting
revenue at risk to executing a bounded recovery workflow and *measuring the money
actually recovered* — across payment failures, checkout abandonment, B2B overdue
receivables, and failed subscriptions — with a randomized control group, a
compliance gate in front of every action, stopping rules that end in human
escalation, and a full audit trail.

```
revenue at risk ──▶ classifier ──▶ case ──▶ selector ──▶ policy gate ──▶ executor
                       ▲                                                      │
                       │             audit trail (every decision, SQLite)      │
                       └───────── recovery / re-plan / escalate / write-off ◀──┘
```

> **The pitch:** most recovery tools report gross recovered money. This agent
> reports *incremental* recovered money against a randomized control group,
> while every action is policy-gated, auditable, and stops safely through
> opt-out or human escalation.

## Judge Run — 5 minutes, no keys

```bash
# Terminal 1 — the agent
RECOVERY_DB=demo.db RAZORPAY_WEBHOOK_SECRET=demo_secret .venv/bin/uvicorn app.main:app --port 8000

# Terminal 2 — the walkthrough
.venv/bin/python scripts/demo.py
```

Then open <http://localhost:8000/> — the demo signs a real failed-payment
webhook, walks it through classification, the policy gate, a `kal pakka`
promise, and a recovery, and lands on the measured lift and the per-case audit
trail. Details: [`scripts/demo.py`](scripts/demo.py).

## The headline (2,000-case simulated batch, 9 loss classes)

| metric | value |
|---|---|
| amount at risk | ₹2.00 Cr across 2,000 cases |
| recovery rate | **70.6% treatment vs 20.8% control** |
| naive retry baseline | ~38% (single dumb retry, no strategy) |
| incremental lift | **+49.7 pp**, 95% CI [+45.6, +53.5] (bootstrap) |
| incremental money recovered | **₹67.6 L** |
| promises-to-pay | 281 captured via inbound replies, 59% keep rate, ₹19.0 L recovered through them |
| Hinglish voice calls | high-value receivables get a TTS call + link-by-SMS follow-through |
| human escalations (compliant exit path) | audit-logged routing to finance ops when ladders exhaust |
| redundant-contact share (would have paid anyway) | 30% — reported honestly |
| opt-outs caused | 21 |

> Fully reproducible: `--seed` fixes the cohort, case ids derive from payment
> ids, and every outcome draw is hashed from `(case_id, salt, seed)` — two runs
> produce identical reports. Simulation parameters are stated assumptions
> (`config.yaml → world:`), not claims. The harness measures whatever behaviour
> you configure — swap the response curves and the same pipeline produces honest
> numbers for them.

![Dashboard: incremental lift, honest costs, per-class breakdown, spend pie, and per-case audit drill-down](docs/dashboard.png)

## What makes it different from a demo

1. **Incremental, not gross.** A stratified randomized control group absorbs
   organic recoveries ("would have paid anyway"). The report's headline is lift,
   not total recovered. A naive retry baseline shows what a dumb single-retry
   strategy achieves — the agent's smart multi-contact ladder does 1.8x better.
2. **The dashboard tells the story in 3 seconds.** A hero section shows the
   incremental recovery number big, with side-by-side treatment vs control vs
   naive baseline bars. No digging through tables required.
2. **Compliance is a first-class gate.** Every action passes one pure-function
   policy engine: quiet hours (IST), rolling attempt caps, cooldowns, opt-out
   registry, human approval above ₹25k, case expiry. Blocks are audit-logged
   with reasons.
3. **Failure-type-aware strategy.** Insufficient-funds retries align to salary
   cycles (1st/5th); transient network failures retry quickly; hard declines
   never re-charge the same instrument (alternate-instrument link instead);
   mandate issues route to re-auth before any charge.
4. **Honest costs.** Contact spend, cost per incremental recovery, redundant
   contacts, and opt-outs are all reported next to the lift.
5. **Every decision is explainable.** `GET /audit/{case_id}` returns the full
   reasoning chain: classification + confidence, chosen strategy + why,
   policy verdicts, execution receipts.
6. **Customers talk back.** `POST /inbound/reply` parses Hinglish replies:
   `kal`/`parso`/`25 tarikh`/`somvar`/`3 din baad` become tracked promises that
   pause the ladder and schedule a follow-up check; `STOP` opts out; `paid`
   closes the case; refusals leave automation with an audit trail.
7. **Voice where it pays for itself.** High-value B2B receivables (≥₹25k) get a
   spoken Hinglish script (TTS) with the payment link sent by SMS in parallel —
   the channel you can't click on still gets the click delivered.
8. **Promise-to-pay has teeth.** A promise isn't a note in a CRM: the dunning
   ladder pauses, a check is scheduled past the due date, and broken promises
   re-enter the workflow automatically — all measured (keep rate, money via
   promises) in the report.
9. **ROI calculator.** Plug in your own numbers — amount at risk, baseline
   recovery, estimated lift — and get a projected incremental recovery, contact
   spend, and cost per recovery. Every assumption is stated.
10. **Statistical honesty.** 95% CI via 2,000-rep percentile bootstrap, seeded
    for reproducibility. Treatment/control stratified by failure class at ingest.
    Naive baseline estimated from world-model parameters.

## Three scenarios, told by the data

**Insufficient funds on the 25th → salary-cycle retry.** The classifier tags
the failure; the selector does *not* fire a same-day retry. It schedules for
10:00 IST on the next salary-cycle day (1st/5th), when balances refill — with
an early nudge if that's more than 3 days out. Simulated cohort (2,000 cases):
INSUFFICIENT_FUNDS recovers **79.7% treatment vs 28.8% control (+50.8 pp)**
across 520 cases.

**Hard decline → never re-charge the instrument.** A blocked/fraud-flagged card
is never retried — compliance and customer trust — instead the nudge carries an
alternate-instrument payment link. Measured: HARD_DECLINE **37.8% vs 9.5%
(+28.2 pp)** against control across 140 cases.

**₹50k B2B invoice, 10 days overdue → escalating ladder ending in humans.**
Stage 1 SMS (+2h) → stage 2 WhatsApp (+1d) → stage 3 voice call at ≥₹25k (+3d)
→ audit-logged escalation to finance ops. No silent drop: relationship cases
end with people. Measured: INVOICE_OVERDUE **73.2% vs 6.2% (+67.0 pp)** across
160 cases.

(Per-class numbers come from the seeded batch run in `report.json`; world-model
parameters are stated assumptions in `config.yaml`, which is exactly why the
control group exists.)

## Run it

```bash
# zero to measured results in one command (no keys needed)
./scripts/quickstart.sh
```

Or step by step:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# offline demo (no keys needed): 2,000-case batch + report
.venv/bin/python scripts/run_batch.py

# dashboard + API
.venv/bin/uvicorn app.main:app --port 8000   # open http://localhost:8000/

# tests
.venv/bin/python -m pytest tests -q
```

- **API docs**: browse `/docs` for the full OpenAPI spec (webhooks, cases,
  scheduler, inbound replies, reporting, and `GET /calculator` — a merchant ROI
  estimate driven entirely by your config economics).
- **Merchant presets** (`configs/templates/`):

  | template | domain | key differences from default |
  |---|---|---|
  | `b2b_receivables.yaml` | overdue invoices | ₹50k human-approval cap, voice on, AP-inbox-first, AP teams reply with dates |
  | `saas_subscriptions.yaml` | failed renewals | 5 gentle touches, ₹10k cap, voice off, no salary-cycle logic |
  | `d2c_checkout.yaml` | cart abandonment | everything inside 48h, ₹10k cap, voice off, fast expiry |

  Run any preset: `RECOVERY_CONFIG=configs/templates/<name>.yaml .venv/bin/python scripts/run_batch.py`
- **Vulcan-ready classification**: `app/classifier_vulcan.py` is a working
  adapter for Razorpay's foundation model — set `VULCAN_API_URL` when a
  merchant API appears and classification routes through it, with silent
  fallback to the rule table on any failure. Assumed contract documented
  in-file; see [FUTURE_ROADMAP.md](FUTURE_ROADMAP.md).
- **Voice without a BSP**: `integrations/mock_voice_provider.py` is a runnable
  stand-in — point `VOICE_PROVIDER_URL` at it to demo the live voice path and
  inspect exactly what would be spoken (`GET /calls`).
- **Ops alerts**: set `SLACK_WEBHOOK_URL` and finance-ops escalations, customer
  opt-outs, refusals, and high-value cases awaiting approval land in Slack the
  moment they happen (best-effort; alert failures never touch the loop).
- **Rate limiting**: 120 req/min per client IP out of the box
  (`RATE_LIMIT_PER_MIN`), 429 + `Retry-After` beyond it — protects webhooks and
  `/calculator` when exposed through a tunnel.
- **Multi-merchant**: send `X-Merchant-Id: <name>` on any request to route that
  merchant to its own fully isolated DB file (`recovery_<name>.db`); no header
  = single tenant, unchanged behavior. Header values are sanitized — path
  traversal cannot escape the data directory.
- **Cost breakdown**: the dashboard renders a spend-by-channel donut
  (WhatsApp / SMS / email / voice) straight from the audit trail's per-action
  costs. The full UI is a single static HTML file + vendored Chart.js — no
  CDN, no build step, works air-gapped; the zero-dependency server-rendered
  report remains as automatic fallback.

## Kubernetes

```bash
helm install rzp charts/rzp-recovery-agent \
  --set image.repository=ghcr.io/OWNER/rzp-recovery-agent \
  --set agentToken=$(openssl rand -hex 16)
```

Deploys the API + a single-replica ticker Deployment (never scale it — two
tickers would double-contact customers), backed by a PVC for SQLite state.
Lint/render verified with Helm v3; move to Postgres before scaling replicas.

Or run it all in Docker — API plus a built-in per-minute `/tick` scheduler,
state persisted in a named volume:

```bash
docker compose up --build          # dashboard on http://localhost:8000/
```

## 5-minute demo (no keys, fully live)

The whole loop — ingestion, classification, strategy, the policy gate, a
customer promise, a recovery, and the measured proof — against a local server:

```bash
# terminal 1: the agent
RECOVERY_DB=demo.db RAZORPAY_WEBHOOK_SECRET=demo_secret \
    .venv/bin/uvicorn app.main:app --port 8000

# terminal 2: the walkthrough
.venv/bin/python scripts/demo.py
```

It signs a real `payment.failed` webhook (→ classification + salary-cycle
strategy), shows real DEFER/BLOCK verdicts from the policy gate and the
hard-decline stopping rule, sends `kal pakka` → promise-to-pay, then `paid` →
recovery, and ends on `/report` and `/audit/{case_id}` — lift, CI, costs,
blocks, and the full reasoning chain. Demo cases land in `demo.db`; the
canonical report stays untouched.

Set `AGENT_API_TOKEN` (e.g. in `.env`) and the scheduler sends it as
`X-Agent-Token`; without a token the operator endpoints stay open — fine for
localhost, never on a public URL.

Live Razorpay test mode: copy `.env.example` → `.env`, fill
`RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET / RAZORPAY_WEBHOOK_SECRET`, then **run
the preflight**:

```bash
.venv/bin/python scripts/live_check.py
```

It verifies, in order: key format (test-mode) → API auth against
`api.razorpay.com` → a ₹1 payment-link creation → a signed webhook round-trip
through the real receiver (valid signature accepted, forged rejected,
`payment_link.paid` marks recovery). All PASS = plumbing proven end to end.

Then wire the traffic:

1. **Dashboard → Settings → Webhooks**: add your URL
   (`https://…/webhooks/razorpay`), secret = same as `RAZORPAY_WEBHOOK_SECRET`,
   subscribe to `payment.failed` and `payment_link.paid`
2. **Expose localhost for testing**: `ngrok http 8000` (or
   `cloudflared tunnel --url http://localhost:8000`)
3. **Run**: `.venv/bin/uvicorn app.main:app --port 8000`
4. **Scheduler**: hit `curl -X POST localhost:8000/tick` on a cron (every minute);
   if `AGENT_API_TOKEN` is set in `.env`, send it as the `X-Agent-Token` header
   (`/tick`, `/cases/*/approve`, `/cases/*/opt_out` reject callers without it)
5. Point your SMS/WhatsApp BSP's inbound replies at `POST /inbound/reply`;
   optionally set `VOICE_PROVIDER_URL` for a TTS/BSP voice stack

Without keys everything runs in simulation mode — identical code paths except
the delivery sink and payment-link creation, which are stubs.

## Repo map

```
app/
  models.py           domain models (money = integer paise everywhere)
  store.py            SQLite persistence + audit log
  notifier.py         Slack ops alerts (escalations, opt-outs) — best-effort
  razorpay_client.py  test-mode HTTP client / recording stub
  classifier.py       error codes -> FailureClass (+confidence); optional LLM fallback
  classifier_vulcan.py optional Vulcan foundation-model adapter (env-gated, falls back to rules)
  selector.py         failure-aware intervention choice (next best action)
  policy.py           compliance/stopping rules — pure functions, unit-tested
  executor.py         runs actions through the gate; voice + channel adapters
  copywriter.py       Hinglish templates + TTS call scripts + opt-out footer
  promisetopay.py     inbound-reply intent parser (kal / parso / tarikh / STOP / paid)
  agent.py            ingest -> plan -> recover/write-off state machine
  measure.py          incremental-lift math, bootstrap CI, per-class breakdown
  static/dashboard.html  the dashboard (Chart.js vendored in static/vendor — no CDN, works offline)
  report_html.py      dependency-free fallback dashboard if the static bundle is missing
  main.py             FastAPI: webhooks, inbound replies, approvals, tick, audit, report, /cases/recent
simulate/
  world.py            latent customer-behaviour model (organic + response + promises)
  batch_generator.py  synthetic cohort w/ realistic Indian failure mix
  engine.py           discrete-event simulation of the full loop
scripts/run_batch.py  end-to-end demo -> report.json
scripts/quickstart.sh one command: venv -> deps -> batch -> results
configs/templates/    merchant presets (B2B receivables / SaaS subs / D2C checkout)
integrations/         mock voice BSP for live demos (no credentials needed)
docs/dashboard.png    live screenshot of the report dashboard
Dockerfile            container image (tzdata included for IST quiet hours)
docker-compose.yml    API + built-in /tick scheduler + persistent volume
charts/               Helm chart: api + ticker + PVC, secrets wired
.github/workflows/    CI (lint+smoke+tests) and ghcr.io image publishing
COMPLIANCE.md         messaging compliance + data handling, claim-by-claim
DEPLOYMENT_CHECKLIST.md  pre-production verification, every item with its check
FUTURE_ROADMAP.md     Vulcan integration story — layers, seams, honest caveats
tests/                policy edges, classifier, parser, voice, promises, e2e smoke
```

## Known limits (read before judging)

- **Recovery completion is webhook-driven.** The public API can create payment
  links / mandate re-auths; it cannot force a card charge. Completion arrives as
  `payment_link.paid`. In simulation the world model plays the customer.
- **The world model is the weakest link.** Response probabilities are plausible
  assumptions, calibrated to be conservative (fatigue decay, quiet-hour penalty),
  but they are assumptions — that is exactly why the measurement layer exists.
- **Single-node SQLite.** Right-sized for a batch harness; swap Postgres when
  there are concurrent webhook writers.
- Optional LLM (any OpenAI-compatible endpoint) only polishes copy/classification;
  every path has a deterministic fallback and the system is fully functional
  without it.

## Where this fits in Razorpay's stack

Layered, not competing: Razorpay's Vulcan foundation model (announced Aug 2026)
answers *what happened to the payment and how to route the next one*; this agent
answers *what bounded, compliant action recovers the money already lost — and
did it actually work vs control*. The classifier is a pluggable seam ready for
Vulcan-enriched failure signals when a merchant-facing API appears. Details and
honest caveats: [FUTURE_ROADMAP.md](FUTURE_ROADMAP.md).
