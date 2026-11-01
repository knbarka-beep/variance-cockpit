-- 04_v_group_month.sql
-- WHAT: Actual vs budget per P&L group (Revenue, Cost of materials, Staff costs,
--       Other operating expenses) plus EBITDA as its own row, for each month and
--       year to date (YTD).
-- HOW:  1. GROUP BY month and P&L group, adding up v_account_month.
--       2. EBITDA = the sum of all groups in ledger sign (UNION ALL adds it as an extra row).
--          In ledger sign revenue is negative and costs positive, so the sum is -EBITDA.
--       3. YTD = a running total within the fiscal year: a window function
--          SUM(...) OVER (PARTITION BY fiscal_year, pl_group ORDER BY period_date).
--          basis = 'month' or 'ytd' says which one a row is.
--       4. Profit view: revenue and EBITDA are shown as positive (sign flipped with
--          CASE WHEN), costs as positive; variance_profit_dkk = budget - actual in ledger
--          sign = effect on EBITDA (positive = favourable).

CREATE OR REPLACE VIEW v_group_month AS
WITH by_group AS (
    SELECT period, period_date, fiscal_year, pl_group,
           SUM(actual_ledger_dkk) AS actual_ledger_dkk,
           SUM(budget_ledger_dkk) AS budget_ledger_dkk
    FROM v_account_month
    GROUP BY period, period_date, fiscal_year, pl_group
),
with_ebitda AS (
    SELECT * FROM by_group
    UNION ALL
    SELECT period, period_date, fiscal_year, 'EBITDA',
           SUM(actual_ledger_dkk), SUM(budget_ledger_dkk)
    FROM by_group
    GROUP BY period, period_date, fiscal_year
),
month_and_ytd AS (
    SELECT 'month' AS basis, * FROM with_ebitda
    UNION ALL
    SELECT 'ytd', period, period_date, fiscal_year, pl_group,
           SUM(actual_ledger_dkk) OVER ytd,
           SUM(budget_ledger_dkk) OVER ytd
    FROM with_ebitda
    WINDOW ytd AS (PARTITION BY fiscal_year, pl_group ORDER BY period_date)
)
SELECT
    period, period_date, fiscal_year, basis, pl_group,
    CASE pl_group WHEN 'Revenue' THEN 1 WHEN 'Cost of materials' THEN 2
                  WHEN 'Staff costs' THEN 3 WHEN 'Other operating expenses' THEN 4
                  ELSE 5 END AS sort_order,
    -- ledger sign
    actual_ledger_dkk,
    budget_ledger_dkk,
    actual_ledger_dkk - budget_ledger_dkk AS variance_ledger_dkk,
    -- profit view
    CASE WHEN pl_group IN ('Revenue', 'EBITDA') THEN -1 ELSE 1 END * actual_ledger_dkk AS actual_dkk,
    CASE WHEN pl_group IN ('Revenue', 'EBITDA') THEN -1 ELSE 1 END * budget_ledger_dkk AS budget_dkk,
    budget_ledger_dkk - actual_ledger_dkk AS variance_profit_dkk,
    ROUND(100.0 * (budget_ledger_dkk - actual_ledger_dkk) / NULLIF(ABS(budget_ledger_dkk), 0), 2) AS variance_pct,
    budget_ledger_dkk - actual_ledger_dkk > 0 AS favourable
FROM month_and_ytd;
