-- 01_base_tables.sql
-- WHAT: Loads the five raw CSV files into tables with explicit data types, and builds
--       a small periods table (one row per month with its fiscal year).
-- HOW:  read_csv with a fixed column list, so a changed file fails loudly instead of
--       being guessed. Amounts are DECIMAL(18,2): exact to the øre, no floating-point
--       rounding. period stays text 'YYYY-MM' (easy to read and join on); period_date is
--       the first day of the month as a real DATE (easy to sort and do date maths on).
-- NOTE: The params table (company name, thresholds, fiscal year start) is created by
--       build_db.py from config/settings.yaml before this file runs.

CREATE OR REPLACE TABLE accounts AS
SELECT * FROM read_csv('data/raw/accounts.csv', header = true, columns = {
    'account_no': 'INTEGER', 'account_name': 'VARCHAR', 'pl_group': 'VARCHAR',
    'allowed_cost_centres': 'VARCHAR'});

CREATE OR REPLACE TABLE cost_centres AS
SELECT * FROM read_csv('data/raw/cost_centres.csv', header = true, columns = {
    'cost_centre': 'VARCHAR', 'code': 'INTEGER', 'description': 'VARCHAR'});

CREATE OR REPLACE TABLE counterparties AS
SELECT * FROM read_csv('data/raw/counterparties.csv', header = true, columns = {
    'counterparty': 'VARCHAR', 'type': 'VARCHAR', 'country': 'VARCHAR',
    'default_account_no': 'INTEGER'});

CREATE OR REPLACE TABLE budget AS
SELECT period,
       CAST(period || '-01' AS DATE) AS period_date,
       account_no, cost_centre, amount_dkk
FROM read_csv('data/raw/budget.csv', header = true, columns = {
    'period': 'VARCHAR', 'account_no': 'INTEGER', 'cost_centre': 'VARCHAR',
    'amount_dkk': 'DECIMAL(18,2)'});

CREATE OR REPLACE TABLE gl_transactions AS
SELECT line_id, voucher_no, posting_date, period,
       CAST(period || '-01' AS DATE) AS period_date,
       account_no, cost_centre, counterparty, description, amount_dkk
FROM read_csv('data/raw/gl_transactions.csv', header = true, columns = {
    'line_id': 'INTEGER', 'voucher_no': 'INTEGER', 'posting_date': 'DATE',
    'period': 'VARCHAR', 'account_no': 'INTEGER', 'cost_centre': 'VARCHAR',
    'counterparty': 'VARCHAR', 'description': 'VARCHAR', 'amount_dkk': 'DECIMAL(18,2)'});

-- Fiscal year runs October-September and is named after the year it ends:
-- October 2025 belongs to FY2026, September 2026 also belongs to FY2026.
-- fiscal_month_no: October = 1 ... September = 12.
CREATE OR REPLACE TABLE periods AS
SELECT DISTINCT
    b.period,
    b.period_date,
    'FY' || CAST(year(b.period_date)
                 + CASE WHEN month(b.period_date) >= p.fiscal_year_start_month THEN 1 ELSE 0 END
                 AS VARCHAR) AS fiscal_year,
    (month(b.period_date) - p.fiscal_year_start_month + 12) % 12 + 1 AS fiscal_month_no
FROM budget b
CROSS JOIN params p;
