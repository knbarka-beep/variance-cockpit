-- 10_v_checks.sql
-- WHAT: Reconciliation checks. Each row is one check: how many items were compared and
--       how many did not match. build_db.py stops with an error if any failures > 0.
-- HOW:  Each check calculates the same number in two different ways and counts the rows
--       where they differ. Amounts are DECIMAL, so "equal" means equal to the øre.
--       IS DISTINCT FROM is used instead of <> so that a missing row (NULL) counts as a
--       mismatch rather than being silently ignored.
--       check_data_counts is loaded by build_db.py from the independent pandas check
--       (check_data.py), so check 6 compares SQL against a separate implementation.

CREATE OR REPLACE VIEW v_checks AS
WITH
-- 1. Ledger lines added up again = actual in v_account_month
tx_vs_account AS (
    SELECT COUNT(*) AS checked,
           COUNT(*) FILTER (WHERE COALESCE(t.tx_sum, 0) IS DISTINCT FROM a.actual_ledger_dkk) AS failures
    FROM v_account_month a
    FULL OUTER JOIN (
        SELECT period, account_no, cost_centre, SUM(amount_ledger_dkk) AS tx_sum
        FROM v_transactions
        GROUP BY period, account_no, cost_centre
    ) t ON t.period = a.period AND t.account_no = a.account_no AND t.cost_centre = a.cost_centre
),
-- 2. P&L groups (and the EBITDA row) = sum of all accounts, per month
acc_month AS (
    SELECT period, SUM(actual_ledger_dkk) AS act, SUM(budget_ledger_dkk) AS bud
    FROM v_account_month GROUP BY period
),
grp_month AS (
    SELECT period,
           SUM(actual_ledger_dkk) FILTER (WHERE pl_group <> 'EBITDA') AS act,
           SUM(budget_ledger_dkk) FILTER (WHERE pl_group <> 'EBITDA') AS bud,
           MAX(actual_ledger_dkk) FILTER (WHERE pl_group = 'EBITDA')  AS ebitda_act,
           MAX(budget_ledger_dkk) FILTER (WHERE pl_group = 'EBITDA')  AS ebitda_bud
    FROM v_group_month WHERE basis = 'month' GROUP BY period
),
group_vs_account AS (
    SELECT COUNT(*) AS checked,
           COUNT(*) FILTER (WHERE a.act IS DISTINCT FROM g.act OR a.bud IS DISTINCT FROM g.bud
                               OR a.act IS DISTINCT FROM g.ebitda_act OR a.bud IS DISTINCT FROM g.ebitda_bud) AS failures
    FROM acc_month a FULL OUTER JOIN grp_month g ON g.period = a.period
),
-- 3. EBITDA bridge: budget EBITDA + all steps = actual EBITDA, month and YTD
bridge AS (
    SELECT COUNT(*) AS checked,
           COUNT(*) FILTER (WHERE start_amount + changes IS DISTINCT FROM end_amount) AS failures
    FROM (
        SELECT period, basis,
               MAX(amount_dkk) FILTER (WHERE step = 'Budget EBITDA') AS start_amount,
               SUM(amount_dkk) FILTER (WHERE step_type = 'change')   AS changes,
               MAX(amount_dkk) FILTER (WHERE step = 'Actual EBITDA') AS end_amount
        FROM v_ebitda_bridge GROUP BY period, basis
    )
),
-- 4. Flexed budget: price/usage + volume = total variance
flexed AS (
    SELECT COUNT(*) AS checked,
           COUNT(*) FILTER (WHERE price_usage_variance_ledger_dkk + volume_variance_ledger_dkk
                                  IS DISTINCT FROM total_variance_ledger_dkk) AS failures
    FROM v_flexed_budget
),
-- 5. Whole ledger: line count and total in the database = the raw CSV file read again
raw_file AS (
    SELECT COUNT(*) AS n, CAST(ROUND(SUM(amount_dkk), 2) AS DECIMAL(18,2)) AS total
    FROM read_csv_auto('data/raw/gl_transactions.csv')
),
ledger_vs_raw AS (
    SELECT 1 AS checked,
           CASE WHEN r.n = d.n AND r.total = d.total THEN 0 ELSE 1 END AS failures
    FROM raw_file r,
         (SELECT COUNT(*) AS n, SUM(amount_ledger_dkk) AS total FROM v_transactions) d
),
-- 6. Material variances per month = what check_data.py (pandas) counted
material_counts AS (
    SELECT COUNT(*) AS checked,
           COUNT(*) FILTER (WHERE k.material_variances IS DISTINCT FROM c.material_count) AS failures
    FROM (SELECT period, material_variances FROM v_kpis WHERE basis = 'month') k
    FULL OUTER JOIN check_data_counts c ON c.period = k.period
),
-- 7. Price rows in the material list = material price/usage variances in v_flexed_budget
price_rows AS (
    SELECT COUNT(*) AS checked,
           COUNT(*) FILTER (WHERE m.variance_profit_dkk IS DISTINCT FROM f.price_usage_variance_profit_dkk
                               OR m.flexed_budget_dkk IS DISTINCT FROM f.flexed_budget_dkk) AS failures
    FROM (SELECT * FROM v_material_variances WHERE variance_type = 'price') m
    FULL OUTER JOIN (SELECT * FROM v_flexed_budget WHERE price_usage_material) f
      ON f.period = m.period AND f.account_no = m.account_no AND f.cost_centre = m.cost_centre
)
SELECT 1 AS check_no, 'Transactions = actual per account, cost centre and month' AS check_name, checked, failures FROM tx_vs_account
UNION ALL SELECT 2, 'P&L groups and EBITDA = sum of accounts, per month', checked, failures FROM group_vs_account
UNION ALL SELECT 3, 'EBITDA bridge: budget + steps = actual (month and YTD)', checked, failures FROM bridge
UNION ALL SELECT 4, 'Flexed budget: price/usage + volume = total variance', checked, failures FROM flexed
UNION ALL SELECT 5, 'Ledger line count and total = raw CSV file', checked, failures FROM ledger_vs_raw
UNION ALL SELECT 6, 'Material variances per month = check_data.py', checked, failures FROM material_counts
UNION ALL SELECT 7, 'Price rows in material list = v_flexed_budget', checked, failures FROM price_rows;
