# Demo Storyboard — 5 Minutes

## Opening Hook [0:00–0:15]

**Screen:** Terminal — run the demo script

```
$ .venv/bin/python scripts/demo.py
```

**Say this:** "This agent recovers ₹67 crore. But that's not the interesting part."

*Pause. Let them wonder what IS the interesting part.*

---

## The Twist [0:15–0:45]

**Screen:** Dashboard hero — Treatment vs Control bars

**Say this:** "Most recovery tools report gross money recovered. We report
*incremental* — money that wouldn't have come in without us.

Treatment: 70.6%. Control: 20.8%. That 49.8 percentage point gap?
That's real value created. The 30% of customers who would've paid anyway?
We report that too.

This is how medicine proves drugs work. This is how recovery
should be measured."

**Key visual:** The two bars side by side. Treatment taller than control.
The gap is the whole point.

---

## The Pipeline [0:45–1:15]

**Screen:** Live demo output flowing in terminal

**Let it run. Narrate over it:**

"Payment fails. Classifier runs — 15 failure types, each gets a different
strategy. Policy gate checks: quiet hours? Opted out? Attempt cap?
Everything audit-logged.

Customer replies 'kal pakka' — Hinglish parser catches it, pauses the
ladder, schedules follow-up. Promise tracked. Payment recovered.
Full reasoning chain, every step."

**Key moment:** When "kal pakka" gets parsed. That's the detail that
makes judges lean in.

---

## The Numbers [1:15–2:00]

**Screen:** Dashboard — scroll through metrics

**Hit these in order:**

1. **₹67.72 Cr** — "Incremental recovery above control"
2. **+49.8 pp** — "Lift. 95% CI: 45.8 to 53.6. Bootstrap, seeded, reproducible."
3. **₹199.58 Cr** — "Total amount at risk across 2,000 cases"
4. **279 promises** — "Hinglish parsing. 59% keep rate. ₹18.83 Cr through promises."
5. **21 opt-outs** — "Honored. Every one. No silent failures."

**Say this:** "30% of our recoveries would've happened anyway. We count
that as a cost, not a win. That's how you earn trust."

---

## The Architecture [2:00–2:30]

**Screen:** README diagram

```
classifier → selector → policy gate → executor
                ↑                          │
                └──── audit trail ◀────────┘
```

**Say this:** "Nine failure classes. Different strategy for each.
Insufficient funds → salary cycle retry. Hard decline → alternate
instrument, never re-charge. Invoice overdue → escalate to humans.

Policy gate is pure functions. Deterministic. Testable. No side effects.
Audit trail is append-only. Can't retroactively fake a decision."

---

## What Broke [2:30–3:15]

**Screen:** Code snippets or just talk

**Tell this story:**

"First version: full LLM classification. Every failure to Groq.
Seemed smart. Then we measured.

400ms per case. ₹0.15 each. 2,000 cases = ₹300. And contradictory
results on similar errors.

We tried rules. 99% accuracy. 5ms. Zero cost.

So we kept Groq for edge cases only — the 5% of error texts that
rules can't parse. Now it costs ₹10 instead of ₹300.

**The lesson:** Don't use AI because it's trendy. Use it where
rules fail. We measured the tradeoff. Rules won. Groq catches
the leftovers."

---

## The Proof [3:15–4:00]

**Screen:** Dashboard — case ledger, open a case, show audit trail

**Say this:** "Every case has a full reasoning chain."

```
webhook received
  → classified: INSUFFICIENT_FUNDS (0.97)
  → policy: EXECUTE (not quiet hours, attempt 1/3)
  → strategy: salary-aligned retry (1st/5th)
  → channel: WhatsApp (UCB1 selected)
  → sent: "Hi Rahul, your payment didn't go through..."
  → reply: "kal pakka" → promise tracked
  → follow-up scheduled: 2026-09-01 10:00 IST
  → payment succeeded
  → measured: incremental (vs control)
```

**Say this:** "This isn't a log. It's a reasoning chain. You can
trace every decision back to its cause. In production, this is
how you pass audits."

---

## Close [4:00–4:30]

**Screen:** Back to dashboard hero

**Say this:** "Revenue recovery is unsolved because most tools
optimize for *appearing* to recover money, not for *creating* value.

We built a system that measures what matters, explains every decision,
respects compliance, and is honest about its limitations.

When Razorpay's Vulcan API ships, we plug it in. When real merchants
run it, the framework holds. The numbers are reproducible.
The audit trail is immutable. The control group is real."

**Final line:** "This isn't a recovery project. It's a measurement
project. Recovery is just how we generate the data."

---

## B-Roll Suggestions

If you want cutaways during narration:

1. **Running the demo** — terminal output flowing
2. **Dashboard charts** — the lift bars, the funnel, the spend doughnut
3. **Code scrolling** — `policy.py` (pure functions), `measure.py` (bootstrap CI)
4. **Case detail modal** — the audit trail expanding
5. **WhatsApp preview** — the message template rendering

## Pacing Notes

- **Don't rush the numbers.** Let judges read them.
- **Pause after "30% would've paid anyway."** That's the honesty moment.
- **Slow down during "What Broke."** That's where you show thinking.
- **End strong.** "Measurement project, not recovery project" is the line they remember.

## If Judges Ask Hard Questions

**"Why not just use Razorpay's built-in recovery?"**
"Razorpay doesn't measure incremental lift. They report gross.
We prove the recovery actually created value."

**"Is 2,000 cases enough?"**
"The CI tells you. 95% CI: 45.8 to 53.6. Narrow enough to be
confident. Wide enough to be honest. The bootstrap is seeded —
you can reproduce it."

**"What's the cost?"**
"₹78K in contact spend for ₹67.72 Cr incremental. That's
₹0.11 per ₹100 recovered. The cost per incremental recovery
is ₹113."

**"Why Hinglish parsing with rules, not ML?"**
"20-word vocabulary. 99% accuracy. Zero latency. Explainable.
In production, you need to explain to compliance why you
sent a message at 2 AM. Regex is easier to audit than a model."
