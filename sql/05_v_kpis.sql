-- 05_v_kpis.sql
-- WHAT: The headline numbers for the top of the dashboard. One row per month and basis
--       ('month' = that month alone, 'ytd' = October up to and including that month):
--       revenue and EBITDA actual vs budget (amount and %), EBITDA margin actual and
--       budget, and the number of material variances.
-- HOW:  1. Turn the Revenue and EBITDA rows of v_group_month into columns ("pivot"),
--          using MAX(...) FILTER (WHERE pl_group = ...).
--       2. Count material variances per month from v_account_month (COUNT(*) FILTER).
--          The YTD count is a running total of the monthly counts within the fiscal year
--          (window function), i.e. the number of material account/cost centre/month cells so far.
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
    SELECT period, fiscal_year, period_date,
           COUNT(*) FILTER (WHERE material) AS material_variances
    FROM v_account_month
    GROUP BY period, fiscal_year, period_date
),
counts AS (
    SELECT period, 'month' AS basis, material_variances FROM monthly_counts
    UNION ALL
    SELECT period, 'ytd',
           SUM(material_variances) OVER (PARTITION BY fiscal_year ORDER BY period_date)
    FROM monthly_counts
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
    CAST(c.material_variances AS INTEGER) AS material_variances
FROM pivoted k
JOIN counts c ON c.period = k.period AND c.basis = k.basis;
