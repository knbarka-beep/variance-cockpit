-- 08_v_transactions.sql
-- WHAT: Every ledger line with its account name, P&L group and fiscal year, for
--       drill-down: "which postings make up this variance?"
-- HOW:  JOIN the ledger to accounts and periods to add the descriptive columns.
--       amount_ledger_dkk is the amount exactly as booked (debit +, credit -);
--       amount_dkk is the profit view (revenue shown positive, CASE WHEN flips the sign).
--       variance_id uses the same recipe as v_material_variances, so the lines behind a
--       variance can be found with WHERE variance_id = '2026-09_4010_Production'.

CREATE OR REPLACE VIEW v_transactions AS
SELECT
    t.line_id,
    t.voucher_no,
    t.posting_date,
    t.period,
    t.period_date,
    per.fiscal_year,
    t.account_no,
    a.account_name,
    a.pl_group,
    t.cost_centre,
    t.counterparty,
    t.description,
    t.amount_dkk AS amount_ledger_dkk,
    CASE WHEN a.pl_group = 'Revenue' THEN -1 ELSE 1 END * t.amount_dkk AS amount_dkk,
    concat_ws('_', t.period, t.account_no, t.cost_centre) AS variance_id
FROM gl_transactions t
JOIN accounts a  ON a.account_no = t.account_no
JOIN periods per ON per.period = t.period;
