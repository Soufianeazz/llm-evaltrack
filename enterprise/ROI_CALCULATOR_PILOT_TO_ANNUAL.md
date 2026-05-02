# ROI Calculator: Pilot to Annual Contract

Stand: 2026-05-02
Owner: Sales + Finance
Status: v1

## 1. Purpose
- Standardize ROI discussion from pilot outcomes to annual contract decision.

## 2. Input Variables
- Monthly LLM calls
- Current failure rate (%)
- Average incident/debugging time per failure
- Engineer hourly cost
- Current model cost per call
- Expected quality improvement (%)
- Expected failure-rate reduction (%)

## 3. Core Formulas
- Baseline monthly failure count:
  - `calls_per_month * failure_rate`
- Baseline monthly failure handling cost:
  - `failure_count * avg_debug_hours_per_failure * engineer_hourly_cost`
- Post-AgentLens failure handling cost:
  - `baseline_failure_cost * (1 - failure_reduction_pct)`
- Baseline model spend:
  - `calls_per_month * current_cost_per_call`
- Optimized model spend:
  - `baseline_model_spend * (1 - model_cost_optimization_pct)`

## 4. Monthly Net Benefit
- `monthly_benefit = (failure_cost_savings + model_cost_savings) - agentlens_monthly_fee`

## 5. Annual ROI
- `annual_benefit = monthly_benefit * 12`
- `roi_pct = (annual_benefit / (agentlens_monthly_fee * 12)) * 100`
- `payback_months = (agentlens_monthly_fee * 12) / max(annual_benefit, 1)`

## 6. Decision Bands
- Strong case:
  - ROI >= 200% and payback <= 6 months
- Medium case:
  - ROI 100-199% and payback <= 12 months
- Weak case:
  - ROI < 100% (review scope, adoption, or pricing assumptions)
