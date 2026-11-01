-- 12_v_customer_month.sql
-- WHAT: Revenue per customer per month, compared with that customer's average for the
--       previous 3 months. Shows which customer explains a revenue variance (used in the
--       AI input for revenue variances).
-- HOW:  1. Add up the revenue lines per customer, account, cost centre and month
--          (profit view: revenue positive).
--       2. Build a grid of every customer x every month (CROSS JOIN with periods) and
--          LEFT JOIN the revenue onto it, so a month without invoices counts as 0
--          instead of being missing. Missing months would make the average wrong.
--       3. Window function with a frame:
--          AVG(revenue) OVER (PARTITION BY customer ORDER BY month
--                             ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING)
--          = the average of the three months before this one (this month itself excluded).
--          The first months of the data have fewer than 3 months before them;
--          months_in_average says how many were used (0 = no average).
-- NOTE: The previous 3 months are not seasonally adjusted. In a low month (July,
--       December) every customer looks down against the months before.

CREATE OR REPLACE VIEW v_customer_month AS
WITH revenue AS (
    SELECT counterparty AS customer, account_no, cost_centre, period,
           SUM(amount_dkk) AS revenue_dkk
    FROM v_transactions
    WHERE pl_group = 'Revenue'
    GROUP BY counterparty, account_no, cost_centre, period
),
grid AS (
    SELECT DISTINCT r.customer, r.account_no, r.cost_centre, p.period, p.period_date
    FROM revenue r
    CROSS JOIN periods p
),
filled AS (
    SELECT g.customer, g.account_no, g.cost_centre, g.period, g.period_date,
           COALESCE(r.revenue_dkk, 0) AS revenue_dkk
    FROM grid g
    LEFT JOIN revenue r
      ON r.customer = g.customer AND r.account_no = g.account_no
     AND r.cost_centre = g.cost_centre AND r.period = g.period
),
with_average AS (
    SELECT *,
           AVG(revenue_dkk) OVER prev3   AS avg_prev_3m,
           COUNT(*)         OVER prev3   AS months_in_average
    FROM filled
    WINDOW prev3 AS (PARTITION BY customer, account_no, cost_centre ORDER BY period_date
                     ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING)
)
SELECT
    customer, account_no, cost_centre, period, period_date,
    revenue_dkk,
    CAST(ROUND(avg_prev_3m, 2) AS DECIMAL(18,2)) AS avg_prev_3_months_dkk,
    CAST(ROUND(revenue_dkk - avg_prev_3m, 2) AS DECIMAL(18,2)) AS change_dkk,
    ROUND(100.0 * (revenue_dkk - avg_prev_3m) / NULLIF(avg_prev_3m, 0), 2) AS change_pct,
    months_in_average
FROM with_average;
