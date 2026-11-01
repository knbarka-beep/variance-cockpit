# SQL guide - Variance Cockpit

**All data is synthetic.** The company and all of its customers and suppliers are fictional.

This guide explains the calculation layer one view at a time. For each view it gives the question it answers, the key SQL idea, and an example row. The SQL files are in `sql/` and run in number order. `scripts/build_db.py` runs them, checks the results and exports JSON for the dashboard.

## The big picture

```
raw CSV files ──► 01 base tables ──► 02 v_account_month ──┬─► 03 v_flexed_budget
                                                          ├─► 04 v_group_month ──┬─► 05 v_kpis
                                                          │                      └─► 06 v_ebitda_bridge
                                                          ├─► 07 v_material_variances
                                                          └─► 09 v_account_trend
                     01 base tables ──► 08 v_transactions
                     everything     ──► 10 v_checks (reconciliation)
       07 + AI drafts + reviews     ──► 11 v_comments
```

**Why views?** A view is a saved query. It holds no data of its own; it is recalculated from the base tables every time. Every number on the dashboard therefore comes from one place, and it can always be traced back to the ledger.

**Why DuckDB?** It is a database in a single file, with no server to install. It is very fast for this kind of analysis (sums and groupings over many rows), and it can read CSV files directly.

**Parameters.** The materiality thresholds, company name and fiscal year start are not typed into the SQL. `build_db.py` copies them from `config/settings.yaml` into a one-row table called `params`. The views read them from there with `CROSS JOIN params`, which attaches that one row to every row.

## Two sign conventions

| | Ledger sign (`*_ledger_dkk`) | Profit view (`*_dkk`) |
|---|---|---|
| Revenue | negative (credit) | positive |
| Costs | positive (debit) | positive |
| Variance | actual - budget; positive = worse | `variance_profit_dkk` = effect on EBITDA; positive = favourable |

The trick: in ledger sign a higher number always means lower profit, for revenue and costs alike. So the effect on EBITDA is simply **budget - actual in ledger sign**, with no special case for revenue. Only the display amounts need a `CASE WHEN pl_group = 'Revenue' THEN -1 ELSE 1 END` to flip revenue to positive.

Percentages are in per cent (8.62 means 8.62 %).

---

## 01 Base tables

**Question:** What does the raw data look like, with the right data types?

**Key SQL idea:** `read_csv` with a fixed list of column types. Amounts are `DECIMAL(18,2)`: exact to the øre, unlike floating-point numbers, which can be off by a tiny fraction. Each month is stored twice: `period` as text (`'2026-09'`, easy to read and join on) and `period_date` as a real date (easy to sort and do date maths on). A small `periods` table works out the fiscal year with `CASE WHEN month >= 10 THEN year + 1`.

**Example row (periods):**

| period | period_date | fiscal_year | fiscal_month_no |
|---|---|---|---|
| 2025-10 | 2025-10-01 | FY2026 | 1 |

## 02 v_account_month

**Question:** For each account, cost centre and month: what was actual, what was budget, how big is the variance, and is it material?

**Key SQL idea:** `GROUP BY period, account, cost centre` to add up the ledger lines. Then a `FULL OUTER JOIN` with the budget, so cells with only budget or only actuals are kept, with `COALESCE(..., 0)` for the missing side. The materiality flag is a true/false expression: `ABS(variance) >= 50000 AND ABS(variance) >= 5 % × ABS(budget)`.

**Example row:** domestic revenue, September 2026 (the key customer's volume cut)

| account | cost centre | actual_ledger | budget_ledger | actual_dkk | budget_dkk | variance_profit_dkk | variance_pct | material | favourable |
|---|---|---|---|---|---|---|---|---|---|
| 1010 Product revenue, domestic | Sales | -5,410,503.42 | -5,920,588.24 | 5,410,503.42 | 5,920,588.24 | -510,084.82 | -8.62 | true | false |

## 03 v_flexed_budget

**Question:** Raw materials are over budget. Is that because we paid more, or because we sold a different volume?

**Key SQL idea:** a CTE (a named sub-query in `WITH`) calculates the volume ratio per month: actual revenue ÷ budget revenue. That ratio is joined back to the materials rows. **Flexed budget = budget × volume ratio** ("what materials should have cost at the volume we actually sold"). Then:

- **Volume variance = flexed budget - budget:** caused by selling more or less.
- **Price/usage variance = actual - flexed budget:** caused by paying more per unit, or using more per unit.

The two add up to the total variance by construction. Check 4 confirms it to the øre.

**Example row:** raw materials, September 2026 (profit view, positive = favourable)

| volume % of budget | actual | budget | flexed budget | total | volume | price/usage | price/usage % |
|---|---|---|---|---|---|---|---|
| 95.3 | 4,476,520 | 4,311,265 | 4,108,487 | -165,256 | +202,778 | -368,034 | -8.96 |

Against the plain budget, materials look 165k over budget, which is under the 5 % threshold. The split shows the real story: lower volume saved 203k, and prices cost 368k (about 9 %).

## 04 v_group_month

**Question:** How did each P&L group, and EBITDA, do this month and year to date?

**Key SQL idea:** `GROUP BY period, pl_group`, then `UNION ALL` to add EBITDA as an extra row (the sum of all groups). YTD uses a **window function**: `SUM(...) OVER (PARTITION BY fiscal_year, pl_group ORDER BY period_date)` gives a running total that restarts each fiscal year. A `basis` column says whether a row is `month` or `ytd`.

**Example rows:** other operating expenses, September 2026

| basis | actual_dkk | budget_dkk | variance_profit_dkk | variance_pct |
|---|---|---|---|---|
| month | 1,614,362.59 | 1,321,666.68 | -292,695.91 | -22.15 |
| ytd | 16,377,336.93 | 15,860,000.16 | -517,336.77 | -3.26 |

## 05 v_kpis

**Question:** What are the headline numbers for the top of the dashboard?

**Key SQL idea:** a **pivot**: turning rows into columns. `MAX(actual_dkk) FILTER (WHERE pl_group = 'Revenue')` picks the revenue row's value into a revenue column. The material variance count uses `COUNT(*) FILTER (WHERE material)`. It is only given for `basis = 'month'`. For YTD it is NULL (`CASE WHEN basis = 'month' THEN ... END`), because materiality is judged month by month.

**Example rows:** September 2026

| basis | revenue actual | revenue budget | rev. var % | EBITDA actual | EBITDA budget | EBITDA var % | margin actual | margin budget | material |
|---|---|---|---|---|---|---|---|---|---|
| month | 10,258,394 | 10,764,706 | -4.70 | 252,317 | 1,548,922 | -83.71 | 2.46 | 14.39 | 5 |
| ytd | 120,562,979 | 122,000,000 | -1.18 | 11,201,701 | 14,640,000 | -23.49 | 9.29 | 12.00 | NULL |

## 06 v_ebitda_bridge

**Question:** How do we get from budget EBITDA to actual EBITDA? Which P&L group explains the gap?

**Key SQL idea:** `UNION ALL` stacks three kinds of rows: the starting total, one change per P&L group, and the ending total. A running total (`SUM(...) OVER (PARTITION BY period, basis ORDER BY step_no)`) gives the start and end height of each bar, ready for a waterfall chart.

**Example:** September 2026, month

| step | amount | bar from | bar to |
|---|---|---|---|
| Budget EBITDA | 1,548,921.56 | 0 | 1,548,921.56 |
| Revenue | -506,312.02 | 1,548,921.56 | 1,042,609.54 |
| Cost of materials | -150,823.77 | 1,042,609.54 | 891,785.77 |
| Staff costs | -346,772.37 | 891,785.77 | 545,013.40 |
| Other operating expenses | -292,695.91 | 545,013.40 | 252,317.49 |
| Actual EBITDA | 252,317.49 | 0 | 252,317.49 |

## 07 v_material_variances

**Question:** Which variances need a comment this month, biggest first?

**Key SQL idea:** two filtered lists stacked with `UNION ALL`:

- **`total` rows:** actual vs budget, from v_account_month `WHERE material`.
- **`price` rows:** actual vs flexed budget for raw materials and packaging, from v_flexed_budget `WHERE price_usage_material`. These catch a price increase that lower volume hides in the total.

The window function `ROW_NUMBER() OVER (PARTITION BY period ORDER BY ABS(variance_profit_dkk) DESC)` ranks the rows within each month.

Two ids are built from the row's own keys with `concat_ws`, so they are the same every time the data is rebuilt:

- **`variance_id`:** the key for the AI layer, e.g. `2026-09_4010_Production`, or `2026-09_2010_Production_price` for a price row.
- **`cell_id`:** the same id without the `_price` suffix. It links a row to its ledger lines in v_transactions.

**Example rows:**

| rank | variance_id | type | account | actual | budget | flexed budget | variance_profit_dkk | % |
|---|---|---|---|---|---|---|---|---|
| 2 | 2026-09_2010_Production_price | price | Raw materials | 4,476,520.35 | 4,311,264.71 | 4,108,486.75 | -368,033.60 | -8.96 |
| 3 | 2026-09_4010_Production | total | Repairs and maintenance | 500,653.91 | 264,333.33 | | -236,320.58 | -89.40 |

## 08 v_transactions

**Question:** Which ledger lines make up this variance? (drill-down)

**Key SQL idea:** a plain `JOIN` of the ledger to accounts and periods, to add names, P&L group and fiscal year. Each line gets a `cell_id` (period_account_costcentre), so `WHERE cell_id = '2026-09_4010_Production'` finds the lines behind a variance.

**Example row:**

| line_id | posting_date | account | counterparty | description | amount_ledger_dkk | cell_id |
|---|---|---|---|---|---|---|
| 2062 | 2026-09-18 | 4010 Repairs and maintenance | Hydra-Service Danmark ApS | Invoice 48213, emergency repair hydraulic press line 2, parts and labour | 350,000.00 | 2026-09_4010_Production |

## 09 v_account_trend

**Question:** Is this variance a one-off or a pattern? (12-month trend chart)

**Key SQL idea:** a **self-join**: the view is joined to itself. For each "end month" it picks the same account's rows from the 11 months before up to that month: `t.period_date BETWEEN e.period_date - INTERVAL 11 MONTH AND e.period_date`.

**Example rows:** repairs, trend ending September 2026

| end_period | month_no | period | actual | budget | variance_profit_dkk | material |
|---|---|---|---|---|---|---|
| 2026-09 | 1 | 2025-10 | 256,303.86 | 264,333.33 | 8,029.47 | false |
| 2026-09 | 12 | 2026-09 | 500,653.91 | 264,333.33 | -236,320.58 | true |

## 10 v_checks (reconciliation)

**Question:** Can we trust the numbers?

**Key SQL idea:** each check calculates the same number in two different ways and counts the rows where they differ (`COUNT(*) FILTER (WHERE a IS DISTINCT FROM b)`). `IS DISTINCT FROM` is used instead of `<>` because it also catches a missing row (NULL). `build_db.py` stops before exporting if any check fails.

| # | Check | What it proves |
|---|---|---|
| 1 | Transactions = actual per account, cost centre and month | Drill-down lines add up to the number shown |
| 2 | P&L groups and EBITDA = sum of accounts | Nothing lost or double-counted when grouping |
| 3 | Bridge: budget + steps = actual | The waterfall closes exactly, month and YTD |
| 4 | Flexed: price/usage + volume = total | The split explains the whole variance |
| 5 | Ledger count and total = raw CSV | Nothing lost when loading the file |
| 6 | Material count = check_data.py | SQL and an independent pandas script agree |
| 7 | Price rows = v_flexed_budget | The price rows in the material list are exactly the material price/usage variances |

I tested that the checks can actually fail. Changing one ledger line by DKK 0.01 makes check 5 fail, and a wrong count makes check 6 fail. Checks 1 to 4 guard against mistakes in the SQL logic itself.

## 11 v_comments

**Question:** For each material variance, what did the AI draft, and what did the controller decide?

**Key SQL idea:** the AI drafts (`data/ai/drafts.json`) and the reviews (`data/ai/reviews.csv`) are loaded as tables. A `LEFT JOIN` puts them next to v_material_variances, so variances without a draft or review still appear (with NULLs). The draft's output is a nested JSON object; DuckDB reads a field inside it with dot notation, e.g. `d.output.comment`. See [ai-layer.md](ai-layer.md).

## 12 v_customer_month

**Question:** Which customer explains a revenue variance?

**Key SQL idea:** first a grid of every customer × every month (`CROSS JOIN`), with the revenue `LEFT JOIN`ed onto it, so a month without invoices counts as 0 instead of being missing. Then a **window function with a frame**: `AVG(revenue) OVER (PARTITION BY customer ORDER BY month ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING)` is the average of the three months *before* this one. The month itself is left out, so it can be compared against them.

**Example row:** the key customer, August 2026

| customer | period | revenue | avg previous 3 months | change | change % |
|---|---|---|---|---|---|
| Nordvik Maskinfabrik A/S | 2026-08 | 1,537,556.21 | 1,820,452.04 | -282,895.83 | -15.54 |

Every other domestic customer was +3 to +6 % that month (July was a low month), so Nordvik stands out.

## 13 v_counterparty_month

**Question:** Which supplier explains a cost variance, and is its spend unusual this month?

**Key SQL idea:** the same pattern as view 12 (grid + `LEFT JOIN` + a window frame for the previous 3 months), applied to costs. `COALESCE(counterparty, '(no counterparty)')` groups payroll and card payments, which have no supplier. `COUNT(*)` adds the number of lines, so one payroll line can be told apart from 27 small card payments.

**Example row:** the planted machine repair, September 2026

| supplier | period | cost | avg previous 3 months | change | lines |
|---|---|---|---|---|---|
| Hydra-Service Danmark ApS | 2026-09 | 350,000.00 | 37,265.58 | 312,734.42 | 1 |

## Interview one-liners

- **"Why not calculate in Python or in the dashboard?"** One place for every number. The dashboard only displays, so it cannot disagree with itself.
- **"How do you handle the sign of revenue?"** The data stays in ledger sign. The views add profit-view columns, and since higher ledger numbers always mean lower profit, the EBITDA effect is budget - actual for every account.
- **"How do you know the numbers are right?"** Six reconciliation checks run on every build, and the build stops if one fails.
- **"What is a window function?"** A calculation across related rows that keeps every row, like a running YTD total. `GROUP BY` would collapse them into one row.
