-- 05_v_kpis.sql
-- WHAT: The headline numbers for the top of the dashboard. One row per month and basis
--       ('month' = that month alone, 'ytd' = October up to and including that month):
--       revenue and EBITDA actual vs budget (amount and %), EBITDA margin actual and
--       budget, and the number of material variances.
-- HOW:  1. Turn the Revenue and EBITDA rows of v_group_month into columns ("pivot"),
--          using MAX(...) FILTER (WHERE pl_group = ...).
--       2. Count material variances per month from v_account_month (COUNT(*) FILTER).
--          The count is only given for basis 'month'; for 'ytd' it is NULL, because
--          materiality is judged per month and a YTD count would mix different months.
--       3. Margin = EBITDA / revenue, in per cent. Variance % = variance / budget, in per cent.
--       All amounts are profit view: positive revenue, positive EBITDA, variance positive = favourable.

CREATE OR REPLACE VIEW v_kpis AS
WITH pivoted AS (
    SELECT period, period_date, fiscal_year, basis,
           MAX(actual_dkk) FILTER (WHERE pl_group = 'Revenue') AS revenue_actual_dkk,
           MAX(budget_dkk) FILTER (WHERE pl_group = 'Revenue') AS revenue_budget_dkk,
           MAX(actual_dkk) FILTER (WHERE pl_group = 'EBITDA')  AS ebitda_actual_dkk,
           MAX(budget_dkk) FILTER (WHERE pl_group = 'EBITDA')  AS ebitda_budget_dkk
    FROM v_group_month
    GROUP BY period, period_date, fiscal_year, basis
),
monthly_counts AS (
    SELECT period, COUNT(*) FILTER (WHERE material) AS material_variances
    FROM v_account_month
    GROUP BY period
)
SELECT
    k.period, k.period_date, k.fiscal_year, k.basis,
    k.revenue_actual_dkk,
    k.revenue_budget_dkk,
    k.revenue_actual_dkk - k.revenue_budget_dkk AS revenue_variance_dkk,
    ROUND(100.0 * (k.revenue_actual_dkk - k.revenue_budget_dkk) / k.revenue_budget_dkk, 2) AS revenue_variance_pct,
    k.ebitda_actual_dkk,
    k.ebitda_budget_dkk,
    k.ebitda_actual_dkk - k.ebitda_budget_dkk AS ebitda_variance_dkk,
    ROUND(100.0 * (k.ebitda_actual_dkk - k.ebitda_budget_dkk) / NULLIF(ABS(k.ebitda_budget_dkk), 0), 2) AS ebitda_variance_pct,
    ROUND(100.0 * k.ebitda_actual_dkk / k.revenue_actual_dkk, 2) AS ebitda_margin_actual_pct,
    ROUND(100.0 * k.ebitda_budget_dkk / k.revenue_budget_dkk, 2) AS ebitda_margin_budget_pct,
    CASE WHEN k.basis = 'month' THEN CAST(c.material_variances AS INTEGER) END AS material_variances
FROM pivoted k
JOIN monthly_counts c ON c.period = k.period;
