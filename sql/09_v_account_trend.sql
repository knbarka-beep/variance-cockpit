-- 09_v_account_trend.sql
-- WHAT: For each account, cost centre and month ("end month"): actual vs budget for the
--       12 months up to and including that month. Feeds the small trend chart in drill-down,
--       so the controller can see whether a variance is a one-off or a pattern.
-- HOW:  A self-join: v_account_month is joined to itself. For every end-month row (e) we
--       pick the rows (t) of the same account and cost centre whose date lies between
--       11 months before and the end month itself. The first months of the data have
--       fewer than 12 months of history, so their trend is shorter.
--       month_no: 1 = oldest month shown, up to 12 = the end month.

CREATE OR REPLACE VIEW v_account_trend AS
SELECT
    e.period AS end_period,
    e.account_no,
    e.account_name,
    e.cost_centre,
    12 - datediff('month', t.period_date, e.period_date) AS month_no,
    t.period,
    t.actual_dkk,
    t.budget_dkk,
    t.variance_profit_dkk,
    t.material
FROM v_account_month e
JOIN v_account_month t
  ON  t.account_no = e.account_no
  AND t.cost_centre = e.cost_centre
  AND t.period_date BETWEEN e.period_date - INTERVAL 11 MONTH AND e.period_date;
