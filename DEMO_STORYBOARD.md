# Demo Storyboard

## [0:00–0:15] Intro

**Screen:** Your face (camera on)

**Say this:**

"Hi, I'm Hemang. I'm a second-year student at the Faculty of
Technology, University of Delhi. I've been thinking about this
problem for a while: how do you know if your revenue recovery
system actually works?

Most tools report gross numbers. I wanted to measure incremental
lift. This is what I built."

---

## [0:15–0:35] What This Is

**Screen:** README — top section

**Say this:**

"This is a revenue recovery agent for Razorpay. It detects failed
payments, decides what to do about each one, executes the action,
and measures whether the recovery actually created value.

Most recovery tools report gross money recovered. We measure
incremental lift using randomized control groups — the same
methodology medicine uses to prove drugs work.

Core result: +49.8 percentage point lift over control. ₹67.72 crore
incremental recovery. 95% confidence interval. Every number
reproducible."

---

## [0:35–1:10] How It Works

**Screen:** Architecture diagram in README

```
classifier → selector → policy gate → executor
                ↑                          │
                └──── audit trail ◀────────┘
```

**Say this:**

"The pipeline is five stages.

Classifier maps error codes to failure types — 9 in this batch, 15 defined.
Each type gets a different strategy — insufficient funds retries on salary
day, hard declines send alternate payment links, invoice overdue
escalates to humans. Every prediction carries SHAP explainability —
you can see exactly which features drove the classification.

Selector picks the best channel — WhatsApp, SMS, email, voice —
using a UCB1 bandit with contextual bias for failure class and
amount tier. The bandit learns from each recovery. Live scores
visible in the dashboard.

Policy gate is pure functions. Quiet hours in IST, attempt caps,
cooldowns, opt-out registry, human approval above ₹25K, case expiry.
Deterministic, testable, no side effects. Every block is audit-logged
with a reason.

Executor sends via the channel selector. Webhook ingestion handles
Razorpay events in under 12 milliseconds sync, then runs background
diagnosis. Audit trail records every decision — append-only, SHA-256
chained, can't be faked after the fact."

---

## [1:10–1:50] Live Walkthrough

**Screen:** Dashboard + terminal side by side

**Run through a case:**

"So let's walk through one case.

A customer tries to pay ₹1,500 with their card. It fails — insufficient
funds.

The classifier picks it up. INSUFFICIENT_FUNDS, 97% confidence.
It knows this is someone who'll probably get paid in a few days.

Now the selector picks WhatsApp. The UCB1 bandit learned that
WhatsApp works best for this type of failure — higher open rates
than SMS or email in India.

The policy gate checks — is it quiet hours? No. First attempt? Yes.
Under ₹25K? Yes. All clear, message goes out.

Here's the WhatsApp preview — you can see the character count,
the button layout, everything before it hits the customer.

Now the customer replies. 'Kal pakka' — basically 'tomorrow for sure.'
The Hinglish parser catches that. It's a promise. The system pauses
the follow-up ladder and schedules the next attempt for salary day.

CUSUM is watching the recovery rate in the background. If it drops,
we get an alert.

A few days later, payment comes in. Case closed. And the whole chain
is logged — nine events, every step traceable. You can pull up the
decision inspector and see the EV calculations, the alternatives
that were rejected, everything."

---

## [1:50–2:40] The Numbers

**Screen:** Dashboard hero section

**Go through each metric:**

"₹199.58 crore at risk across 2,000 cases.

Treatment recovery: 70.6%. Control recovery: 20.8%. The gap —
49.8 percentage points — is value created by this agent.

95% confidence interval: 45.8 to 53.6. Bootstrap, 2,000
replications, seeded for reproducibility.

₹67.72 crore incremental recovery.

Cost: ₹78,000 in contact spend. That's ₹113 per incremental
recovery. The ROI calculator lets merchants plug in their own
numbers — amount at risk, baseline recovery, estimated lift —
and get projected incremental recovery with every assumption stated.

279 promises captured through Hinglish parsing. 59% keep rate.
₹18.83 crore recovered through promises.

21 customers opted out. All honored. Zero silent failures.

And the number we report honestly: 30% of recovered customers
would have paid anyway. We count that as a cost, not a win.

The recovery funnel shows where cases drop off — 148 ingested,
194 eligible, 106 recovered. Drop-off reasons tracked: promise
paused, retries exceeded, case expiry."

---

## [2:40–3:10] Per-Class Strategy

**Screen:** Dashboard — scroll to per-class breakdown

**Say this:**

"Different failures, different strategies, different results.

Insufficient funds: 79.7% treatment vs 28.8% control. Salary-cycle
retries work — people get paid on the 1st and 5th.

Hard decline: 37.8% vs 9.5%. Never re-charge the same card.
Send an alternate link instead. The classifier knows this is
a compliance boundary.

Invoice overdue: 73.2% vs 6.2%. Highest lift. Because these
escalate to humans — voice calls with Hinglish TTS scripts,
payment link sent by SMS in parallel. The voice provider
interface is pluggable — mock for demo, real BSP in production.

One size doesn't fit all. The classifier determines the strategy.
The strategy determines the outcome. Portfolio optimization
selects the best subset of cases for human-review capacity
using 0/1 knapsack DP."

---

## [3:10–3:40] What We Learned

**Screen:** Just talk, or show code if you want

**Tell this story:**

"First version sent every failure to an LLM for classification.
Groq Qwen. Seemed like the right thing to do.

Then we measured. 400 milliseconds per case. Fifteen paise each.
Two thousand cases — three hundred rupees. And the LLM gave
contradictory results on similar error codes.

We tried rules instead. Same accuracy. Five milliseconds. Zero cost.

So we kept the LLM for edge cases only — the 5% of unusual error
texts that rules can't parse. Now the whole system costs ten rupees
instead of three hundred. Provider switching in the dashboard
toggles between mock, Ollama, and Claude — you can test each
provider live.

The lesson: measure the tradeoff. Don't assume AI is better.
Sometimes rules are. We proved it."

---

## [3:40–4:10] Future: Vulcan Integration

**Screen:** README or diagram

**Say this:**

"Razorpay announced Vulcan — their payments foundation model.
Four billion transactions, three thousand signals per payment.
It tells you why a payment failed.

We don't compete with Vulcan. We sit on top of it.

Vulcan is Layer 1 — what happened and why. This agent is Layer 2 —
what to do about money already at risk. Measurement is Layer 3 —
did Layer 2 work.

When Razorpay exposes Vulcan signals through their API, the
classifier already has a pluggable interface. We drop in Vulcan's
richer failure reasons. Everything downstream — selector, policy
gate, audit trail — stays the same. The Vulcan adapter is already
in the codebase, waiting.

We built the integration seam before we needed it."

---

## [4:10–4:50] Compliance and Security

**Screen:** Security tab + case audit trail

**Say this:**

"Every case has an immutable audit trail. SHA-256 chained —
you can verify the chain hasn't been tampered with from the
dashboard.

webhook received → classified → policy verdict → strategy selected →
message sent → customer replied → promise tracked → follow-up
scheduled → payment confirmed → measured as incremental.

You can pull up any case and trace the full reasoning chain.
In production, this is how you pass audits.

Policy gate blocks are logged with reasons. Opt-outs are honored.
Quiet hours are enforced. Human approval required above ₹25K.
No silent failures.

Security posture: threat model with mitigations, adversarial
LLM testing — prompt injection attempts are classified as
UNKNOWN with low confidence. The LLM has no tool access, no
credentials, no PII. Every money action requires compliance
gate pass."

---

## [4:50–5:00] Close

**Screen:** Back to dashboard hero

**Say this:**

"Revenue recovery is unsolved because most tools optimize for
appearing to recover money, not for creating value.

We built a system that measures what matters, explains every
decision, respects compliance, and is honest about its limitations.

The numbers are reproducible. The audit trail is immutable.
The control group is real."

---

## Notes

- **Total time:** ~5:00
- **Tone:** Direct, technical, no hype. Let the numbers speak.
- **Pacing:** Slow during numbers. Fast during architecture.
- **The 30% line.** Say it, pause. That's the credibility moment.
- **Vulcan section.** Don't oversell. "Built the seam before we needed it" is enough.

## Features Mentioned

| Feature | Where | How |
|---------|-------|-----|
| SHAP explainability | Architecture | "Every prediction carries SHAP" |
| UCB1 bandit | Architecture + Walkthrough | "Contextual bias, live scores" |
| Webhook ingestion | Architecture | "<12ms sync, background diagnosis" |
| Audit trail (SHA-256) | Architecture + Security | "Append-only, chained, verifiable" |
| WhatsApp concierge | Walkthrough | "Live preview, character count" |
| CUSUM detector | Walkthrough | "Monitors recovery rate" |
| Decision inspector | Walkthrough | "EV calculations, rejected alternatives" |
| ROI calculator | Numbers | "Merchants plug in own numbers" |
| Recovery funnel | Numbers | "Drop-off tracking" |
| Promise-to-pay | Numbers + Walkthrough | "Hinglish parsing, keep rate" |
| Voice TTS | Per-class | "Hinglish scripts, pluggable provider" |
| Portfolio optimization | Per-class | "Knapsack DP for human capacity" |
| Provider switching | What We Learned | "Mock, Ollama, Claude toggle" |
| Vulcan adapter | Future | "Pluggable interface, already in codebase" |
| Adversarial testing | Security | "Prompt injection → UNKNOWN" |
| Multi-currency | Q&A | "USD, EUR, INR with live rates" |
| Auto-pilot | (dashboard visible) | Topbar toggle |
| Settings editor | (dashboard visible) | Engine tab |
| Approval queue | Numbers | "21 opt-outs honored" |

## Q&A Prep

**"Why not use Razorpay's built-in recovery?"**
"Razorpay doesn't measure incremental. They report gross. We prove
the recovery created value."

**"Is 2,000 cases statistically significant?"**
"The CI tells you. 45.8 to 53.6. Narrow enough to be confident.
Wide enough to be honest. Bootstrap is seeded — reproduce it yourself."

**"What does this cost in production?"**
"₹78K contact spend for ₹67.72 Cr incremental. ₹113 per incremental
recovery. Contact costs come from config — merchants set their own."

**"Why rules over ML for Hinglish?"**
"20-word vocabulary. 99% accuracy. Zero latency. Explainable.
You need to tell compliance why a message went out at 2 AM.
Regex is easier to audit than a model."

**"How does Vulcan change things?"**
"Better classifier inputs. That's it. Selector, policy gate,
audit trail, measurement — all unchanged. We designed for that plug."

**"What about international payments?"**
"Multi-currency support is built in — USD, EUR, INR with live
rate conversion. The measurement framework is currency-agnostic."
