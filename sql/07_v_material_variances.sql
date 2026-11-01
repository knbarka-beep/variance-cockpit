-- 07_v_material_variances.sql
-- WHAT: The list of material variances, per month, biggest first. This is the work list
--       the AI will draft comments for and the controller will review.
-- HOW:  1. Keep only the rows of v_account_month where material = true (WHERE).
--       2. variance_id = period_account_costcentre, e.g. '2026-09_4010_Production'.
--          It is built from the row's own keys, so it is stable: the same variance gets
--          the same id every time the data is rebuilt. The AI layer will use it as a key.
--       3. rank_in_month = 1 for the biggest absolute effect on EBITDA in that month
--          (window function ROW_NUMBER() OVER (PARTITION BY period ORDER BY ...)).
--          Ties are broken by account and cost centre so the order never changes randomly.

CREATE OR REPLACE VIEW v_material_variances AS
SELECT
    concat_ws('_', period, account_no, cost_centre) AS variance_id,
    ROW_NUMBER() OVER (PARTITION BY period
                       ORDER BY ABS(variance_profit_dkk) DESC, account_no, cost_centre) AS rank_in_month,
    period, period_date, fiscal_year,
    account_no, account_name, pl_group, cost_centre,
    actual_ledger_dkk, budget_ledger_dkk, variance_ledger_dkk,
    actual_dkk, budget_dkk, variance_profit_dkk, variance_pct,
    favourable
FROM v_account_month
WHERE material
ORDER BY period, rank_in_month;
