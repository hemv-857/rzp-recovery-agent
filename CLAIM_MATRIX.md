# Claim Matrix — Razorpay Revenue Recovery Agent

Every public claim backed to a file, test, or run command.

| Claim | Evidence |
|-------|----------|
| **67 interventions executed** | `scripts/demo.py` → generates `demo.db` with 67 cases, `app/measure.py` prints `Interventions executed: 67` |
| **96% completion rate** | `app/measure.py:build_report()` → `completion_rate = completed / total`. Run `scripts/demo.py` → report shows 96%. |
| **41% recovery rate (vs 17% naive)** | `app/measure.py:naive_baseline()` computes 17% (10/60 treatment recoveries ÷ 60). 41% = 25/60. Both in `build_report()` output. |
| **+24pp incremental lift** | `report["incremental_recovery_rate"]` = `treatment_recovery_rate - naive_recovery_rate`. Printed in report summary. |
| **Bootstrap 95% CI: [+15pp, +33pp]** | `app/measure.py:_bootstrap_ci()` → 10,000 resamples, percentile method. Pseudocode validated in `tests/test_measure.py::test_build_report_has_naive_baseline`. |
| **14-day cohort window** | `config.yaml: "analysis_window_days": 14`. Used in `scripts/demo.py` to generate test data with `fake.date_time_between("-14d", "now")`. |
| **Deterministic time in tests** | `conftest.py:fixed_now()` monkeypatches `datetime.now` and `time.time`. Every test file imports it. |
| **7 compliance rules** | `app/policy.py:evaluate()` — 7 gates: recovered/written_off check, opt-out, money action cap, attempt cap, cooldown, case expiry, quiet hours. Each has a dedicated test in `tests/test_policy.py`. |
| **Failure-aware selector** | `app/selector.py:select_next_action()` — different actions for NETWORK_TIMEOUT, AUTH_DECLINE, SOFT_DECLINE, INSUFFICIENT_FUNDS. Tested in `tests/test_selector.py`. |
| **ML recovery probability** | `app/recovery_model.py:predict_recovery()` → HistGradientBoostingClassifier (400 trees) with rule-based fallback. Trained on 49+ episode outcomes. |
| **Explanation reasoning chain** | `app/explain.py:explain_decision()` → failure context, amount context, attempt fatigue, method reasoning, model prediction, strategy justification. All 4 action types tested. |
| **Degradation detector** | `app/degradation.py:DegradationDetector` — tracks failure rates by global/method/class scope, states HEALTHY→WATCH→CONFIRMED. Tested in `tests/test_ml_explain_degradation.py`. |
| **Economic stopping rule** | `app/policy.py:economic_stop()` — stops when `expected_recovery < 3x action_cost`. Tested in `tests/test_policy.py::test_economic_stop_*`. |
| **Chart.js memory leak fixed** | `app/static/dashboard.html` — `createIfNotExist()` pattern with `window._chart1`/`window._chart2`. Tested in `tests/test_main.py::test_dashboard_contains_chartjs`. |
| **Input length validation** | `app/main.py` — `len(billing_id) > 64` → 400. Tested in `tests/test_main.py::test_billing_id_length_rejection`. |
| **97 tests passing** | `pytest tests/ -q` → `97 passed` |
| **Zero hardcoded keys** | `grep -r "sk_live\|sk_test\|key_live\|key_test" app/` → no matches. All secrets via env vars. |
| **React dashboard via CDN** | `app/static/dashboard.html` — loads React 18 + Babel standalone from unpkg, no build step. Tested in `tests/test_main.py::test_dashboard_contains_chartjs`. |
| **Custom 404 page** | `app/static/404.html` — animated glitch 404, scanline, particles, terminal output. Served via FastAPI 404 exception handler in `app/main.py`. |
| **Multi-seed evaluation** | `scripts/evaluate.py` — 5 seeds × 2,500 cases = 7,500 total, pooled bootstrap CI. Results in `evaluation_report.json`. |
| **Sensitivity analysis** | `scripts/sensitivity.py` — ±20% sweep on base_pay_probability, all lifts positive. Results in `sensitivity_report.json`. |
| **Held-out evaluation** | `scripts/heldout_eval.py` — seed 999 held-out set (separate from training seed 42). Results in `heldout_evaluation.json`. |
| **Webhook idempotency** | `app/store.py` — `webhook_events` table, `is_event_processed()` / `mark_event_processed()`, checked at webhook handler top in `app/main.py`. |
| **Portfolio optimizer (0/1 knapsack)** | `app/portfolio.py:knapsack_select()` — maximizes EV within human-review hour capacity. Demo in `scripts/portfolio_demo.py`. |
| **SHAP per-case explainability** | `app/recovery_model.py:RecoveryModel._explain()` — TreeExplainer for per-case signed SHAP values. Falls back to feature_importances_. |
| **India-specific compliance** | `app/policy.py:evaluate()` — RBI e-mandate pre-debit notice (≥₹5000 first attempt), TRAI quiet hours (21:00–09:00 IST). |
| **Promise-to-pay EV feedback** | `app/promisetopay.py:PromiseTracker.adjust_ev()` — adjusts EV by customer promise reliability. Used in `app/selector.py`. |
| **Provider switching (Mock/Ollama/Claude)** | `app/main.py:/provider` endpoints — live toggle with source tags on each transaction. Mirrors Manojkumar1710. |
| **SSE batch progress** | `app/main.py:/batch/run/stream` — Server-Sent Events stream for live batch run progress. Mirrors Swarajkarle. |
| **14 failure categories** | `app/models.py:FailureClass` + `app/classifier.py:_RULES` — CARD_EXPIRED, GATEWAY_TIMEOUT, PRICE_SHOCK, OVERDUE_GENUINE added. |
| **Case detail timeline with Hinglish scripts** | `app/main.py:/cases/{case_id}/detail` — full timeline: detection → diagnosis → intervention → outcome. |
| **Editable compliance settings** | `app/main.py:/settings` — max_attempts, quiet_hours, DND list, discount_pct, escalation_threshold. Mirrors Swarajkarle. |
| **Cryptographic hash-chained audit trail** | `app/audit_chain.py:AuditChain` — SHA-256 chain (H_i = SHA256(H_{i-1} || step || payload)), verify endpoint. Mirrors modiviveks. |
| **Payment network degradation detector** | `app/network_health.py:NetworkHealthMonitor` — rolling success rates per method, MODERATE/CRITICAL flags. Mirrors modiviveks. |
| **Recovery funnel with drop-off accounting** | `app/main.py:/analytics/funnel` — 4 stages + drop-offs (retries_exceeded, opt_out, awaiting_approval, promise_paused, negative_ev). Mirrors modiviveks, bhuvanteja. |
| **Model calibration view (10-decile)** | `app/main.py:/analytics/calibration` — predicted vs observed per decile, Brier score, ROC-AUC. Mirrors modiviveks. |
| **Decision inspector with rejected alternatives** | `app/main.py:/cases/{id}/decision` — EV calculations, policy decisions, rejected reasons for all candidates. Mirrors modiviveks. |
| **Explicit NO_ACTION when EV negative** | `app/selector.py:select_next_action` — evaluates all candidates, returns None if max net EV <= 0. Mirrors modiviveks. |
| **Segment breakdown by amount tier** | `app/main.py:/analytics/segments` — Standard/Growth/Enterprise tiers with recovery rates. Mirrors modiviveks. |
| **Audit chain verification endpoint** | `app/main.py:/audit/chain/verify` — validates SHA-256 chain integrity. Mirrors modiviveks. |
| **Live_verified vs Demo_verified webhook modes** | `app/agent.py:mark_recovered` + `app/main.py` webhook handler — explicit verification mode (cryptographic vs simulation). Mirrors Ahan-aura. |
| **Exponential backoff for external APIs** | `app/main.py:exponential_backoff` — 0.5s * 2^n with jitter, max 3 retries. Mirrors Ahan-aura. |
| **Rehearsed seed for reproducible demo** | `app/main.py:/batch/run/stream?rehearsed=true` — fixed seed 42 for consistent ~34-36% recovery. Mirrors arpit1021-ux. |
| **Handled gracefully page for hard-decline** | `app/main.py:/handled-gracefully` — deterministically picked case agent correctly refused. Mirrors arpit1021-ux. |
| **LLM-vs-Rules Gate override contrast** | `app/main.py:/cases/{id}/gate-contrast` — shows LLM diagnosis vs Rules Gate verdict. Mirrors arpit1021-ux. |
| **Probabilistic outcome model (demo mode)** | `app/main.py:_demo_recovery_prob` — transparent heuristic by failure class/amount/attempts. Mirrors arpit1021-ux. |
| **Self-hosted fonts / no external deps** | `app/static/dashboard.html` — system-ui font stack, no Google Fonts. Mirrors arpit1021-ux. |
| **Demo verification endpoint** | `app/main.py:/demo/verify/{case_id}` — simulate payment with demo_verified label. Mirrors Ahan-aura. |

## How to reproduce

```bash
# Core demo + API
RECOVERY_DB=demo.db RAZORPAY_WEBHOOK_SECRET=demo_secret .venv/bin/python scripts/demo.py
RECOVERY_DB=demo.db RAZORPAY_WEBHOOK_SECRET=demo_secret .venv/bin/uvicorn app.main:app --port 8000
.venv/bin/python -m pytest tests/ -q

# Evaluation scripts
.venv/bin/python scripts/evaluate.py       # 5-seed eval → evaluation_report.json
.venv/bin/python scripts/sensitivity.py    # ±20% sweep → sensitivity_report.json
.venv/bin/python scripts/heldout_eval.py   # Held-out eval → heldout_evaluation.json
```

## What is NOT claimed

- No claim of production deployment or live payment processing
- No claim of real Razorpay API integration (test mode only)
- No claim of specific revenue recovered (demo data only)
- No claim of model accuracy on unseen production data
