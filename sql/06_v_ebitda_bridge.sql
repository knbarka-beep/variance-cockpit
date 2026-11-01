-- 06_v_ebitda_bridge.sql
-- WHAT: The EBITDA bridge (waterfall chart) from budget EBITDA to actual EBITDA, per
--       month and YTD: start at budget EBITDA, add the variance of each P&L group,
--       end at actual EBITDA.
-- HOW:  1. Stack rows from v_group_month with UNION ALL:
--            step 0: Budget EBITDA                      (step_type 'total')
--            steps 1-4: profit-view variance per group  (step_type 'change')
--            step 5: Actual EBITDA                      (step_type 'total')
--          Because each group variance is budget - actual in ledger sign, and EBITDA is
--          the sum of the groups, budget + steps = actual exactly (checked in 10_v_checks).
--       2. bar_start_dkk / bar_end_dkk say where each bar starts and ends in the chart.
--          A running total (window function SUM OVER ... ORDER BY step_no) gives the level
--          after each step; total bars start at 0.

CREATE OR REPLACE VIEW v_ebitda_bridge AS
WITH steps AS (
    SELECT period, period_date, fiscal_year, basis,
           0 AS step_no, 'Budget EBITDA' AS step, 'total' AS step_type, budget_dkk AS amount_dkk
    FROM v_group_month WHERE pl_group = 'EBITDA'
    UNION ALL
    SELECT period, period_date, fiscal_year, basis,
           sort_order, pl_group, 'change', variance_profit_dkk
    FROM v_group_month WHERE pl_group <> 'EBITDA'
    UNION ALL
    SELECT period, period_date, fiscal_year, basis,
           5, 'Actual EBITDA', 'total', actual_dkk
    FROM v_group_month WHERE pl_group = 'EBITDA'
),
running AS (
    SELECT *,
           SUM(CASE WHEN step_no = 5 THEN 0 ELSE amount_dkk END)
               OVER (PARTITION BY period, basis ORDER BY step_no) AS level_after_step
    FROM steps
)
SELECT
    period, period_date, fiscal_year, basis, step_no, step, step_type, amount_dkk,
    CASE WHEN step_type = 'total' THEN 0 ELSE level_after_step - amount_dkk END AS bar_start_dkk,
    CASE WHEN step_type = 'total' THEN amount_dkk ELSE level_after_step END     AS bar_end_dkk
FROM running;
