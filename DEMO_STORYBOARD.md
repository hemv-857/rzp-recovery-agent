# Demo Storyboard

## [0:00–0:20] What This Is

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

## [0:20–0:50] How It Works

**Screen:** Architecture diagram in README

```
classifier → selector → policy gate → executor
                ↑                          │
                └──── audit trail ◀────────┘
```

**Say this:**

"The pipeline is five stages.

Classifier maps error codes to 15 failure types. Each type gets a
different strategy — insufficient funds retries on salary day,
hard declines send alternate payment links, invoice overdue
escalates to humans.

Selector picks the best channel — WhatsApp, SMS, email, voice —
using a UCB1 bandit that learns which channel works for which
failure type.

Policy gate is pure functions. Quiet hours, attempt caps, opt-outs,
human approval above 25K. Deterministic, testable, no side effects.

Executor sends the message. Audit trail records every decision.
Append-only. Can't be faked after the fact."

---

## [0:50–1:30] Live Walkthrough

**Screen:** Dashboard + terminal side by side

**Run through a case:**

"Payment fails — ₹1,500, card, insufficient funds.

Classifier: INSUFFICIENT_FUNDS, confidence 0.97.

Selector: WhatsApp. UCB1 chose it because WhatsApp has the highest
recovery rate for this failure type.

Policy gate: pass. Not quiet hours. First attempt. Under ₹25K
approval threshold.

Message sent. Customer replies 'kal pakka' — Hinglish parser
catches it. Promise tracked. Ladder pauses. Follow-up scheduled
for next salary day.

Payment comes in. Case closed. Full reasoning chain logged —
nine events, every step traceable."

---

## [1:30–2:15] The Numbers

**Screen:** Dashboard hero section

**Go through each metric:**

"₹199.58 crore at risk across 2,000 cases.

Treatment recovery: 70.6%. Control recovery: 20.8%. The gap —
49.8 percentage points — is value created by this agent.

95% confidence interval: 45.8 to 53.6. Bootstrap, 2,000
replications, seeded for reproducibility.

₹67.72 crore incremental recovery.

Cost: ₹78,000 in contact spend. That's ₹113 per incremental
recovery.

279 promises captured through Hinglish parsing. 59% keep rate.
₹18.83 crore recovered through promises.

21 customers opted out. All honored. Zero silent failures.

And the number we report honestly: 30% of recovered customers
would have paid anyway. We count that as a cost, not a win."

---

## [2:15–2:45] Per-Class Strategy

**Screen:** Dashboard — scroll to per-class breakdown

**Say this:**

"Different failures, different strategies, different results.

Insufficient funds: 79.7% treatment vs 28.8% control. Salary-cycle
retries work — people get paid on the 1st and 5th.

Hard decline: 37.8% vs 9.5%. Never re-charge the same card.
Send an alternate link instead.

Invoice overdue: 73.2% vs 6.2%. Highest lift. Because these
escalate to humans — phone calls, not just messages.

One size doesn't fit all. The classifier determines the strategy.
The strategy determines the outcome."

---

## [2:45–3:15] What We Learned

**Screen:** Just talk, or show code if you want

**Tell this story:**

"First version sent every failure to an LLM for classification.
Seemed like the right thing to do.

Then we measured. 400 milliseconds per case. Fifteen paise each.
Two thousand cases — three hundred rupees. And the LLM gave
contradictory results on similar error codes.

We tried rules instead. Same accuracy. Five milliseconds. Zero cost.

So we kept the LLM for edge cases only — the 5% of unusual error
texts that rules can't parse. Now the whole system costs ten rupees
instead of three hundred.

The lesson: measure the tradeoff. Don't assume AI is better.
Sometimes rules are. We proved it."

---

## [3:15–3:45] Future: Vulcan Integration

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
gate, audit trail — stays the same.

We built the integration seam before we needed it."

---

## [3:45–4:15] Compliance and Audit

**Screen:** Case detail modal — audit trail

**Say this:**

"Every case has an immutable audit trail.

webhook received → classified → policy verdict → strategy selected →
message sent → customer replied → promise tracked → follow-up
scheduled → payment confirmed → measured as incremental.

You can pull up any case and trace the full reasoning chain.
In production, this is how you pass audits.

Policy gate blocks are logged with reasons. Opt-outs are honored.
Quiet hours are enforced. Human approval required above ₹25K.
No silent failures."

---

## [4:15–4:30] Close

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

- **Total time:** ~4:30
- **Tone:** Direct, technical, no hype. Let the numbers speak.
- **Pacing:** Slow during numbers. Fast during architecture.
- **The 30% line.** Say it, pause. That's the credibility moment.
- **Vulcan section.** Don't oversell. "Built the seam before we needed it" is enough.

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
