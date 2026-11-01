-- 07_v_material_variances.sql
-- WHAT: The list of material variances, per month, biggest first. This is the work list
--       the AI drafts comments for and the controller reviews. Two kinds of rows:
--       - variance_type 'total': actual vs budget, for any account (from v_account_month)
--       - variance_type 'price': actual vs flexed budget for raw materials and packaging
--         (from v_flexed_budget), when that price/usage variance is material on its own.
--         This catches a price increase that is hidden by lower volume.
-- HOW:  1. Two SELECTs with WHERE material, stacked with UNION ALL.
--       2. variance_id is built from the row's own keys, so it is stable across rebuilds:
--          '2026-09_4010_Production' (total) or '2026-06_2010_Production_price' (price).
--          The AI layer uses it as its key.
--       3. cell_id = period_account_costcentre for both kinds. It links a row to its ledger
--          lines in v_transactions (WHERE cell_id = ...).
--       4. For price rows the variance is measured against flexed_budget_dkk;
--          budget_dkk is still the original budget, for reference.
--       5. rank_in_month = 1 for the biggest absolute effect on EBITDA in the month
--          (window function ROW_NUMBER), ties broken by id so the order never changes.

CREATE OR REPLACE VIEW v_material_variances AS
WITH total_rows AS (
    SELECT
        'total' AS variance_type,
        concat_ws('_', period, account_no, cost_centre) AS variance_id,
        concat_ws('_', period, account_no, cost_centre) AS cell_id,
        period, period_date, fiscal_year, account_no, account_name, pl_group, cost_centre,
        actual_ledger_dkk, budget_ledger_dkk, variance_ledger_dkk,
        actual_dkk, budget_dkk,
        CAST(NULL AS DECIMAL(18,2)) AS flexed_budget_dkk,
        variance_profit_dkk, variance_pct, favourable
    FROM v_account_month
    WHERE material
),
price_rows AS (
    SELECT
        'price' AS variance_type,
        concat_ws('_', period, account_no, cost_centre, 'price') AS variance_id,
        concat_ws('_', period, account_no, cost_centre) AS cell_id,
        period, period_date, fiscal_year, account_no, account_name,
        'Cost of materials' AS pl_group, cost_centre,
        actual_dkk AS actual_ledger_dkk,          -- costs: ledger sign = profit view
        budget_dkk AS budget_ledger_dkk,
        price_usage_variance_ledger_dkk AS variance_ledger_dkk,
        actual_dkk, budget_dkk, flexed_budget_dkk,
        price_usage_variance_profit_dkk AS variance_profit_dkk,
        price_usage_variance_pct AS variance_pct,
        price_usage_variance_profit_dkk > 0 AS favourable
    FROM v_flexed_budget
    WHERE price_usage_material
),
all_rows AS (
    SELECT * FROM total_rows
    UNION ALL
    SELECT * FROM price_rows
)
SELECT
    variance_id,
    ROW_NUMBER() OVER (PARTITION BY period
                       ORDER BY ABS(variance_profit_dkk) DESC, variance_id) AS rank_in_month,
    *  EXCLUDE (variance_id)
FROM all_rows
ORDER BY period, rank_in_month;
