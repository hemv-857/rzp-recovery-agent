# Competitive Analysis — Track 03: AI Revenue Recovery

## Competitors Found (8 public repos)

| # | Repo | Key Strength |
|---|---|---|
| 1 | AaditPani-RVU/Backstop | 343 tests, 6 seeds, 148k orders, 4-arm backtest |
| 2 | agastyasharma20/revenue-recovery-agent | 111 tests, LinUCB bandit, knapsack optimization, voice, real Razorpay |
| 3 | Harshavardhan-1712/RECLAIM | React frontend, Gemini explainability, isotonic regression |
| 4 | AdithyaAbburi/RecoverAI | Local LLM (Ollama), ERV-based ranking |
| 5 | shwetakanth09/recoverai | 10K cases, in-browser demo, tool-calling agent |
| 6 | allknowledge34/razorpay-ai-revenue-recovery | XGBoost + SHAP explainability |
| 7 | Manojkumar1710/razorpay-ai-revenue-recovery | Advisory ML model, deterministic guardrails |
| 8 | Supritha316/RecoverAI | Live provider switching, Ollama fallback |

---

## Our Cons (Weaknesses vs Competitors)

### 1. Test count is low
- **Us:** 67 tests
- **Backstop:** 343 tests (5x more)
- **agastyasharma20:** 111 tests (1.7x more)
- **Impact:** Judges may perceive less coverage. Volume signals rigor.

### 2. Simulation scale is small
- **Us:** 2,000 seeded cases
- **Backstop:** 148,000 orders across 6 seeds
- **shwetakanth09:** 10,000 synthetic cases
- **agastyasharma20:** 5 seeds with head-to-head comparison
- **Impact:** Larger scale = more credible results. 2k looks thin vs 148k.

### 3. No multi-seed reproducibility
- **Us:** 1 seed (deterministic but single)
- **Backstop:** 6 seeds with per-seed breakdown
- **agastyasharma20:** 5 seeds, agent wins 5/5
- **Impact:** Single seed could be cherry-picked. Multiple seeds prove robustness.

### 4. No real Razorpay test-mode integration
- **agastyasharma20:** Real Razorpay test-mode payment links, real Slack webhooks
- **Us:** Simulation only (stub client)
- **Impact:** "Works with real Razorpay" beats "works in simulation" for credibility.

### 5. Compliance engine is narrower
- **Backstop:** 16 rules including cross-surface per-person fatigue (6/fortnight), stolen card detection, disputed invoice suppression
- **agastyasharma20:** NPCI retry limits, RBI pre-debit notice, TRAI quiet hours, B2B 90-day AR window
- **Us:** Quiet hours, cooldowns, attempt caps, opt-out, human approval
- **Impact:** Our gate is solid but competitors cover more regulatory surfaces.

### 6. No ML/AI model
- **agastyasharma20:** LinUCB contextual bandit, 0/1 knapsack portfolio optimization, Isolation Forest anomaly detection
- **RECLAIM:** Isotonic regression calibration
- **allknowledge34:** XGBoost + SHAP
- **Manojkumar1710:** scikit-learn advisory model
- **Us:** Rule-based classifier only (no learning)
- **Impact:** Judges may see rules as "table stakes" vs ML as "AI". We're the only team with zero ML.

### 7. No LLM integration
- **agastyasharma20:** Groq/Gemini with multi-provider fallback
- **RECLAIM:** Gemini explainability
- **AdithyaAbburi:** Local Ollama (DeepSeek-Coder)
- **Supritha316:** Claude/Ollama/mock toggle
- **Us:** Optional LLM only for copy polish (not core)
- **Impact:** "AI Buildathon" — no AI model looks weak on paper.

### 8. No live frontend
- **RECLAIM:** React/Vite/Tailwind on Vercel
- **agastyasharma20:** React/Vite/TS frontend
- **shwetakanth09:** React/Vite/Tailwind
- **Us:** Single HTML file with Chart.js
- **Impact:** React frontend looks more "production" than a static HTML page.

### 9. No explainability/interpretability
- **agastyasharma20:** SHA-256 hash-chained audit trail, explainable decisions
- **allknowledge34:** SHAP values
- **RECLAIM:** Gemini-generated explanations
- **Us:** Audit trail (good) but no SHAP/LIME/LLM explanations
- **Impact:** Judges may want to see *why* the model chose an action, not just that it did.

### 10. No anomaly detection
- **agastyasharma20:** Isolation Forest for fraud/spike detection
- **Us:** None
- **Impact:** Missing a safety layer that detects unusual patterns.

---

## Our Strengths (vs Competitors)

### 1. Only team with bootstrap 95% CI on lift
No competitor reports confidence intervals. We're the only statistically defensible claim.

### 2. Only team with voice + Hinglish
agastyasharma20 has voice scripts but no real TTS/BSP integration. We have a full voice provider adapter + SMS follow-through.

### 3. Only team with promise-to-pay intent parser
Hinglish NLP: kal/parso/tarikh/somvar/STOP/paid parsed from inbound replies. No competitor has this.

### 4. Only team with naive baseline comparison
We show treatment vs control vs naive retry. Others compare to do-nothing or naive only.

### 5. Only team with Docker + Helm
Production deployment ready. Competitors are uv-only or docker-compose.

### 6. Only team with ROI calculator
Judges can plug in their own numbers and see projected recovery.

### 7. Failure-type-aware strategies
Salary cycle timing, hard decline handling, B2B escalation ladder — more nuanced than generic retry.

### 8. Deterministic seeded simulation
Fully reproducible. Same seed = same results every time.

---

## Summary

| Dimension | Us | Best Competitor |
|---|---|---|
| Tests | 67 | Backstop (343) |
| Seeds | 1 | Backstop (6) |
| Scale | 2K | Backstop (148K) |
| Bootstrap CI | **Yes** | None |
| Voice + Hinglish | **Yes** | None full |
| Promise-to-pay | **Yes** | None full |
| Compliance rules | 5 gates | Backstop (16 rules) |
| ML/AI model | None | agastyasharma20 (LinUCB + knapsack) |
| LLM integration | Optional | agastyasharma20 (Groq/Gemini) |
| Live frontend | HTML | RECLAIM (React/Vercel) |
| Deployment | **Docker + Helm** | Docker only |
| ROI calculator | **Yes** | None |
| Naive baseline | **Yes** | shwetakanth09 (~35% vs ~72%) |
| Real Razorpay | No | agastyasharma20 |
