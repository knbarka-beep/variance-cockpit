-- 02_v_account_month.sql
-- WHAT: Actual vs budget per account, cost centre and month. This is the core view;
--       almost every other view is built on top of it.
-- HOW:  1. Add up the ledger lines per account, cost centre and month (GROUP BY).
--       2. Put them next to the budget with a FULL OUTER JOIN, so a cell with budget but
--          no postings (or postings but no budget) is still included, with 0 for the missing side.
--       3. Add two sets of columns:
--          - ledger sign (debit +, credit -), exactly as in the ledger: *_ledger_dkk
--          - profit view, for the dashboard: revenue and costs both shown as positive
--            amounts (CASE WHEN flips the sign of revenue), and
--            variance_profit_dkk = effect on EBITDA (positive = favourable).
--       In ledger sign a higher number always means lower profit, for revenue and costs
--       alike, so the effect on EBITDA is simply budget - actual.
--       variance_pct = variance_profit_dkk / budget, in per cent (negative = unfavourable).
--       material: |variance| >= the DKK threshold AND >= the % threshold of budget
--       (both read from the params table).

CREATE OR REPLACE VIEW v_account_month AS
WITH actual AS (
    SELECT period, account_no, cost_centre,
           SUM(amount_dkk) AS actual_ledger_dkk
    FROM gl_transactions
    GROUP BY period, account_no, cost_centre
),
cells AS (
    SELECT COALESCE(b.period, a.period)           AS period,
           COALESCE(b.account_no, a.account_no)   AS account_no,
           COALESCE(b.cost_centre, a.cost_centre) AS cost_centre,
           COALESCE(a.actual_ledger_dkk, 0)       AS actual_ledger_dkk,
           COALESCE(b.amount_dkk, 0)              AS budget_ledger_dkk
    FROM budget b
    FULL OUTER JOIN actual a
      ON  a.period = b.period
      AND a.account_no = b.account_no
      AND a.cost_centre = b.cost_centre
)
SELECT
    c.period,
    per.period_date,
    per.fiscal_year,
    c.account_no,
    acc.account_name,
    acc.pl_group,
    c.cost_centre,
    -- ledger sign (as booked)
    c.actual_ledger_dkk,
    c.budget_ledger_dkk,
    c.actual_ledger_dkk - c.budget_ledger_dkk AS variance_ledger_dkk,
    -- profit view (for the dashboard)
    CASE WHEN acc.pl_group = 'Revenue' THEN -1 ELSE 1 END * c.actual_ledger_dkk AS actual_dkk,
    CASE WHEN acc.pl_group = 'Revenue' THEN -1 ELSE 1 END * c.budget_ledger_dkk AS budget_dkk,
    c.budget_ledger_dkk - c.actual_ledger_dkk AS variance_profit_dkk,
    ROUND(100.0 * (c.budget_ledger_dkk - c.actual_ledger_dkk)
          / NULLIF(ABS(c.budget_ledger_dkk), 0), 2) AS variance_pct,
    ABS(c.actual_ledger_dkk - c.budget_ledger_dkk) >= p.materiality_min_dkk
        AND ABS(c.actual_ledger_dkk - c.budget_ledger_dkk) >= p.materiality_pct * ABS(c.budget_ledger_dkk)
        AS material,
    c.budget_ledger_dkk - c.actual_ledger_dkk > 0 AS favourable
FROM cells c
JOIN accounts acc ON acc.account_no = c.account_no
JOIN periods per  ON per.period = c.period
CROSS JOIN params p;
