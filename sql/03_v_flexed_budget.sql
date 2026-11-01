-- 03_v_flexed_budget.sql
-- WHAT: Splits the variance on raw materials and packaging into a volume part and a
--       price/usage part, per month.
-- HOW:  1. Volume ratio per month = actual revenue / budget revenue. Selling prices are
--          fixed in this data, so this ratio is the actual sales volume compared with budget.
--       2. Flexed budget = budget x volume ratio, rounded to the øre: "what materials
--          should have cost at the volume we actually sold".
--       3. Volume variance     = flexed budget - budget  (caused by selling more or less)
--          Price/usage variance = actual - flexed budget (caused by paying more, or using more per unit)
--          Together they add up to the total variance (actual - budget), by construction.
--       Same method as check_data.py. Amounts are costs, so ledger sign and profit view
--       amounts are the same; variances are given in both signs.
--       Profit view: positive = favourable (e.g. lower volume gives a positive volume variance).

CREATE OR REPLACE VIEW v_flexed_budget AS
WITH volume AS (
    SELECT period,
           SUM(actual_ledger_dkk) / SUM(budget_ledger_dkk) AS volume_ratio
    FROM v_account_month
    WHERE pl_group = 'Revenue'
    GROUP BY period
),
flexed AS (
    SELECT a.period, a.period_date, a.fiscal_year,
           a.account_no, a.account_name, a.cost_centre,
           v.volume_ratio,
           a.actual_ledger_dkk AS actual_dkk,
           a.budget_ledger_dkk AS budget_dkk,
           CAST(ROUND(a.budget_ledger_dkk * v.volume_ratio, 2) AS DECIMAL(18,2)) AS flexed_budget_dkk
    FROM v_account_month a
    JOIN volume v ON v.period = a.period
    WHERE a.pl_group = 'Cost of materials'
)
SELECT
    f.period, f.period_date, f.fiscal_year,
    f.account_no, f.account_name, f.cost_centre,
    ROUND(100 * f.volume_ratio, 2) AS volume_pct_of_budget,
    f.actual_dkk,
    f.budget_dkk,
    f.flexed_budget_dkk,
    -- ledger sign: positive = cost higher than budget
    f.actual_dkk - f.budget_dkk         AS total_variance_ledger_dkk,
    f.actual_dkk - f.flexed_budget_dkk  AS price_usage_variance_ledger_dkk,
    f.flexed_budget_dkk - f.budget_dkk  AS volume_variance_ledger_dkk,
    -- profit view: effect on EBITDA, positive = favourable
    f.budget_dkk - f.actual_dkk         AS total_variance_profit_dkk,
    f.flexed_budget_dkk - f.actual_dkk  AS price_usage_variance_profit_dkk,
    f.budget_dkk - f.flexed_budget_dkk  AS volume_variance_profit_dkk,
    ROUND(100.0 * (f.flexed_budget_dkk - f.actual_dkk) / NULLIF(f.flexed_budget_dkk, 0), 2)
        AS price_usage_variance_pct,
    ABS(f.actual_dkk - f.flexed_budget_dkk) >= p.materiality_min_dkk
        AND ABS(f.actual_dkk - f.flexed_budget_dkk) >= p.materiality_pct * ABS(f.flexed_budget_dkk)
        AS price_usage_material
FROM flexed f
CROSS JOIN params p;
