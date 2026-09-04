# Demo Storyboard

## [0:00–0:10] Cold Open

**Screen:** Terminal. Type the command.

```bash
$ .venv/bin/python scripts/demo.py
```

**Say nothing.** Let the output start flowing. Let them see "STEP 0 — seed 150 simulated cases."

*Then:*

"Five minutes. No API keys. Every number real."

---

## [0:10–0:40] The Punchline

**Screen:** Dashboard loads. Hero section. Treatment bar tall. Control bar short.

**Let them look at it for 3 seconds. Then:**

"See that gap? Treatment: 70%. Control: 20%. That 50-point gap is
money we created that wouldn't exist without this agent.

Every other recovery tool reports the tall bar. We report the gap.
That's the only number that matters."

**Don't explain more. Let the visual do the work.**

---

## [0:40–1:10] How It Works

**Screen:** Terminal output from demo — the webhook, the classification, the reply

**Talk over the output:**

"Payment fails. Fifteen failure types — each one gets a different
strategy. Insufficient funds? Retry on salary day. Hard decline?
Send an alternate payment link, never re-charge the same card.

Customer replies 'kal pakka.' The parser catches it. Pauses the
dunning ladder. Schedules a follow-up. Tracks whether they actually
pay.

Every step logged. Every decision explained. You can pull up any
case and trace the full reasoning chain."

**Key beat:** When "kal pakka" parses. That's the moment they lean in.

---

## [1:10–1:50] The Honest Numbers

**Screen:** Scroll through dashboard metrics

**One by one. Pause on each:**

"₹67.72 crore — incremental, not gross.

+49.8 percentage points — the lift over control. 95% confidence
interval: 45.8 to 53.6. Bootstrap. Seeded. Reproduce it yourself.

279 promises captured. Hinglish parsing. 59% keep rate. ₹18.83 crore
recovered through promises alone.

21 customers said stop. We stopped. No silent failures.

And here's the number most teams hide: 30% of our 'recoveries' would
have happened anyway. We count that as a cost. That's how you earn
trust."

**The 30% line is the most important thing you say.**

---

## [1:50–2:20] The Architecture

**Screen:** README diagram

```
classifier → selector → policy gate → executor
                ↑                          │
                └──── audit trail ◀────────┘
```

**Say this, fast:**

"Classifier picks the failure type. Selector picks the strategy.
Policy gate says yes or no — quiet hours, attempt caps, opt-outs,
human approval above 25K. Executor sends. Audit trail records.

Policy gate is pure functions. No side effects. Deterministic.
You can test every rule without running the whole system."

---

## [2:20–3:00] What Broke

**Screen:** Just you talking, or code if you want visuals

**Tell this story:**

"First version sent every failure to an LLM. Seemed smart.

Then we measured. 400 milliseconds per case. Fifteen paise each.
Two thousand cases — three hundred rupees. And the LLM gave
contradictory results on similar error codes.

We tried rules instead. Same accuracy. Five milliseconds. Zero cost.

So we kept the LLM for edge cases only — the five percent of
weird error texts that rules can't parse. Now it costs ten rupees
instead of three hundred.

The lesson: don't use AI because it's impressive. Use it where
rules actually fail. We measured the difference. Rules won."

---

## [2:50–3:20] Future: Vulcan Integration

**Screen:** README or just talk

**Say this:**

"Razorpay announced Vulcan — their payments foundation model.
Four billion transactions. Three thousand signals per payment.
It tells you *why* a payment failed.

We don't compete with that. We sit on top of it.

Vulcan is Layer 1 — what happened and why. We're Layer 2 —
what to do about the money already at risk. Layer 3 is
measurement — did Layer 2 actually work?

When Razorpay exposes Vulcan signals through their API, we
plug in here."

**Point at the classifier in the diagram.**

"The classifier already has a pluggable interface. When Vulcan
sends richer failure reasons, the classifier uses them. Everything
downstream — selector, policy gate, audit trail — stays the same.

We built the seam before we needed it. That's how you ship
fast when the API drops."

---

## [3:20–4:00] The Proof

**Screen:** Open a case in the dashboard. Show the audit trail.

**Read it out:**

"Payment failed. Classified as insufficient funds, confidence 0.97.
Policy said execute — not quiet hours, first attempt, under 25K.
Strategy: salary-cycle retry. Channel: WhatsApp. Customer replied
'kal pakka.' Promise tracked. Follow-up scheduled. Payment came in.
Case measured as incremental.

That's nine events. Full chain. Immutable. You cannot retroactively
change what happened."

---

## [4:00–4:30] Close

**Screen:** Back to the hero section

**Say this:**

"Most recovery tools optimize for looking good. We optimize for
being right.

This is a measurement system that happens to recover payments.
When the numbers are right, the business trusts the system.
When the business trusts the system, it scales.

The framework is ready. The numbers are reproducible.
The audit trail is immutable."

**Last line, slow:**

"Revenue recovery is unsolved because nobody measures incremental
lift. Now someone does."

---

## Notes

- **Total time:** ~4:30. Leaves buffer for transitions.
- **Pacing:** Fast during architecture, slow during numbers and honesty moments.
- **The 30% line.** Say it, pause, let it land.
- **The Vulcan section.** Don't oversell. "We built the seam before we needed it" is the line.
- **End on the last line.** Don't add "thank you" or "any questions." Just stop.

## Q&A Prep

**"Why not just use Razorpay's recovery?"**
"Razorpay doesn't measure incremental. They report gross.
We prove the recovery created value."

**"2,000 cases enough?"**
"The CI tells you. 45.8 to 53.6. Narrow enough to be confident.
Wide enough to be honest."

**"What's the actual cost?"**
"₹78K in contact spend for ₹67.72 Cr incremental. That's
₹113 per incremental recovery."

**"Why rules over ML for Hinglish?"**
"Twenty-word vocabulary. Ninety-nine percent accuracy.
Zero latency. Explainable. In production, you need to tell
compliance why a message went out at 2 AM. Regex is easier
to audit than a model."

**"How does Vulcan change things?"**
"It makes the classifier better. That's it. Selector, policy
gate, audit trail, measurement — all unchanged. We designed
for that plug."
