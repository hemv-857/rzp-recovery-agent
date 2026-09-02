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
| **Economic stopping rule** | `app/policy.py:economic_stop()` — stops when `expected_recovery < 3x action_cost`. Integrated in `app/selector.py`. |
| **ML recovery model** | `app/recovery_model.py` — HistGradientBoostingClassifier (400 trees) with rule-based fallback. |
| **Explanation reasoning chain** | `app/explain.py:explain_decision()` — failure context, amount context, attempt fatigue, method reasoning, model prediction, strategy justification. |
| **Degradation detector** | `app/degradation.py:DegradationDetector` — tracks failure rates by scope, HEALTHY→WATCH→CONFIRMED states. |

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
