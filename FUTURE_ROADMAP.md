# Future Integration: Razorpay Vulcan

## Positioning — the three layers

```
Layer 1  Razorpay Vulcan            "What happened to this payment — and what
         (payments foundation        will make the next one succeed?"
         model, announced Aug 2026)      failure root-cause signals, routing,
         proprietary, on-platform        fraud, checkout personalisation

Layer 2  This agent                 "Given what happened, what should we do
                                    about the money already at risk — within
                                    compliance bounds?"    strategy selection,
                                        policy gates, promise-to-pay, escalation

Layer 3  Measurement                "Did Layer 2 actually work? By how much,
                                    at what cost?"   randomized control group,
                                        incremental lift with CIs
```

We do not compete with Vulcan and do not re-implement it. Vulcan decides
payments *before and while* they happen; this agent owns what happens *after*
a failure, bounded by policy and proven by control-group measurement.

## What Vulcan is (public facts, Aug 18 2026 launch)

- India's first transformer-based AI payments foundation model; built with
  NVIDIA + AWS (SageMaker), architecture and training data proprietary.
- Trained on ~4 billion payments / ~3 trillion data points, reading ~3,000
  signals per transaction.
- In production inside Razorpay's own decisioning: smart routing, network-level
  fraud detection, checkout personalisation.
- **Not available to merchants as a callable API today.** When Razorpay exposes
  Vulcan-derived signals (enriched webhook payloads, failure-reason APIs, or a
  developer surface), this agent is architected to consume them.

## Integration seams that already exist in this repo

1. **Classification input** — `app/classifier.py::classify()` maps error codes +
   descriptions to `FailureClass` (+confidence). It is deliberately pluggable:
   deterministic rule table first, optional LLM fallback, `UNKNOWN` handled
   conservatively downstream. A Vulcan-enriched failure reason would replace or
   augment the rule table's inputs — nothing else changes:

   ```python
   # future, pseudocode — no such public API exists yet
   cls, conf = vulcan_failure_reason(payment_event)  # e.g. HARD_DECLINE @ 0.97
   if cls is None:                                   # graceful degradation
       cls, conf = classify(raw_code, description, method)
   ```

2. **Confidence propagates already** — `agent.ingest_failure` keeps the higher-
   confidence source and policy treats low confidence conservatively (UNKNOWN ⇒
   email-only ladder). Sharper upstream signals flow through without code
   changes on our side.

3. **Strategy table is class-keyed** — `selector.py` chooses per-FailureClass
   strategies (salary-cycle retries, never-recharge-hard-declines, B2B ladders).
   Finer-grained upstream classes map to finer-grained rows in one dict.

4. **Predictive prioritisation (future)** — a Vulcan-style recovery-likelihood
   score could reorder the work queue (high-expected-value cases first) and tune
   `world:` response priors. The selector takes `(case, cfg, now)` and needs no
   structural change to accept a score field.

## Measurement is the arbiter — including for classifiers

Because treatment/control assignment and incremental-lift math are independent
of how classification happens, any Vulcan-powered upgrade is itself A/B-testable
in this harness: run both classifiers over the same cohort and compare lift,
cost per incremental recovery, and redundant-contact share. Upgrades get proven,
not assumed — same standard we hold every other component to.

## What stays ours regardless

Compliance gating (quiet hours, caps, opt-outs, ₹25k human-approval bound),
contact-channel economics and fatigue modelling, Hinglish promise-to-pay
handling, human escalation as the terminal path, audit trail, and the control-
group measurement layer. Vulcan improving failure understanding makes Layer 2's
decisions better informed — it does not replace them.

## Timeline

Watch for Razorpay developer access to Vulcan-derived signals (API alpha,
enriched webhooks). The integration cost on our side is a classifier-provider
swap behind one function plus config — hours, not weeks.
