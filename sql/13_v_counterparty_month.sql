-- 13_v_counterparty_month.sql
-- WHAT: Cost per supplier per month, compared with that supplier's average for the previous
--       3 months on the same account and cost centre. Shows whether one supplier's spend is
--       unusual and explains a cost variance (used in the AI input for cost variances).
-- HOW:  Same method as 12_v_customer_month:
--       1. Add up the cost lines per supplier, account, cost centre and month, and count them.
--          Lines without a counterparty (payroll, card payments, expense claims) are grouped
--          as '(no counterparty)'. The line count shows whether that group is one payroll line
--          or many small purchases.
--       2. Grid of every supplier x every month (CROSS JOIN) with the costs LEFT JOINed onto
--          it, so a month without invoices counts as 0.
--       3. Window function with a frame: AVG(...) OVER (... ROWS BETWEEN 3 PRECEDING AND
--          1 PRECEDING) = the average of the three months before this one.
-- NOTE: Not seasonally adjusted, and a 3-month average of a lumpy cost (marketing, repairs)
--       is itself noisy.

CREATE OR REPLACE VIEW v_counterparty_month AS
WITH cost AS (
    SELECT COALESCE(counterparty, '(no counterparty)') AS counterparty,
           account_no, cost_centre, period,
           SUM(amount_dkk) AS cost_dkk,
           COUNT(*)        AS lines
    FROM v_transactions
    WHERE pl_group <> 'Revenue'
    GROUP BY ALL
),
grid AS (
    SELECT DISTINCT c.counterparty, c.account_no, c.cost_centre, p.period, p.period_date
    FROM cost c
    CROSS JOIN periods p
),
filled AS (
    SELECT g.counterparty, g.account_no, g.cost_centre, g.period, g.period_date,
           COALESCE(c.cost_dkk, 0) AS cost_dkk,
           COALESCE(c.lines, 0)    AS lines
    FROM grid g
    LEFT JOIN cost c
      ON c.counterparty = g.counterparty AND c.account_no = g.account_no
     AND c.cost_centre = g.cost_centre AND c.period = g.period
),
with_average AS (
    SELECT *,
           AVG(cost_dkk) OVER prev3 AS avg_prev_3m,
           AVG(lines)    OVER prev3 AS avg_lines_prev_3m,
           COUNT(*)      OVER prev3 AS months_in_average
    FROM filled
    WINDOW prev3 AS (PARTITION BY counterparty, account_no, cost_centre ORDER BY period_date
                     ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING)
)
SELECT
    counterparty, account_no, cost_centre, period, period_date,
    cost_dkk,
    CAST(ROUND(avg_prev_3m, 2) AS DECIMAL(18,2)) AS avg_prev_3_months_dkk,
    CAST(ROUND(cost_dkk - avg_prev_3m, 2) AS DECIMAL(18,2)) AS change_dkk,
    ROUND(100.0 * (cost_dkk - avg_prev_3m) / NULLIF(avg_prev_3m, 0), 2) AS change_pct,
    lines,
    ROUND(avg_lines_prev_3m, 1) AS avg_lines_prev_3_months,
    months_in_average
FROM with_average;
