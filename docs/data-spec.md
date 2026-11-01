# Data specification - Variance Cockpit

**All data described here is synthetic.** Odense Demo Manufacturing ApS and all of its customers and suppliers are fictional.

This document explains what the data contains and how it is made. It is written for finance readers. Every number mentioned here comes from `config/settings.yaml`. To change an assumption, edit that file and run `scripts/generate_data.py` again.

## 1. The company

| Item | Value |
|---|---|
| Name | Odense Demo Manufacturing ApS (fictional) |
| Business | Manufacturer of machined and welded components for industrial customers |
| Revenue | About DKK 120m a year (budget FY2025: 118m, FY2026: 122m) |
| Employees | About 80 |
| Cost centres | Production (100), Sales (200), Administration (300) |
| Period | 24 calendar months, October 2024 to September 2026 |
| Fiscal year | October to September, named after the year it ends (FY2025 = Oct 2024 to Sep 2025) |
| P&L scope | Down to EBITDA only (no depreciation, interest or tax) |
| Currency | DKK |

## 2. Files

| File | Purpose |
|---|---|
| `data/raw/accounts.csv` | Chart of accounts |
| `data/raw/cost_centres.csv` | Cost centres |
| `data/raw/counterparties.csv` | Customers and suppliers |
| `data/raw/budget.csv` | Monthly budget per account and cost centre |
| `data/raw/gl_transactions.csv` | Actuals: individual general ledger lines |
| `data/truth/planted_events.csv` | Answer key for testing. **Never used as input to the AI or the dashboard.** |
| `data/check/variance_check.xlsx` | Made by `check_data.py` for manual checks in Excel. Not committed to git. |

CSV files are in machine format: comma-separated, UTF-8, dot as decimal separator, no thousands separator. Amounts have two decimals.

## 3. Sign convention

The data uses the same convention as a real general ledger: **debit is positive, credit is negative.**

- Revenue is negative (a sale is a credit to the revenue account).
- Costs are positive.
- A reversal has the opposite sign of the line it reverses.
- The budget uses the same convention.
- EBITDA = minus the sum of all lines. For example, revenue of -10m and costs of +9m gives EBITDA of 1m.

This gives a simple rule for variances, where **variance = actual − budget**:

- **A positive variance always lowers profit (unfavourable)**, for revenue and costs alike. Revenue of -9m against a budget of -10m gives a variance of +1m: one million less revenue.
- **A negative variance always raises profit (favourable).**

Dashboards and reports can flip the signs for human readers later. The raw data keeps the ledger convention.

## 4. Tables and columns

### accounts.csv

| Column | Meaning |
|---|---|
| account_no | Four-digit account number. First digit = P&L group (1 revenue, 2 materials, 3 staff, 4 other expenses) |
| account_name | English account name |
| pl_group | One of: Revenue, Cost of materials, Staff costs, Other operating expenses |
| allowed_cost_centres | Cost centres the account can be posted to, separated by `;` |

The chart has 15 accounts:

| No. | Name | P&L group | Cost centres |
|---|---|---|---|
| 1010 | Product revenue, domestic | Revenue | Sales |
| 1020 | Product revenue, export | Revenue | Sales |
| 2010 | Raw materials | Cost of materials | Production |
| 2020 | Packaging | Cost of materials | Production |
| 3010 | Wages and salaries | Staff costs | Production, Sales, Administration |
| 3020 | Overtime | Staff costs | Production |
| 3030 | Temporary staff | Staff costs | Production |
| 3040 | Pension and social security costs | Staff costs | Production, Sales, Administration |
| 4010 | Repairs and maintenance | Other operating expenses | Production |
| 4020 | Energy | Other operating expenses | Production |
| 4030 | Rent | Other operating expenses | Administration |
| 4040 | IT costs | Other operating expenses | Administration |
| 4050 | Marketing | Other operating expenses | Sales |
| 4060 | Travel | Other operating expenses | Sales, Administration |
| 4090 | Other external costs | Other operating expenses | Production, Sales, Administration |

### cost_centres.csv

| Column | Meaning |
|---|---|
| cost_centre | Name used in the budget and ledger (Production, Sales, Administration) |
| code | Three-digit code (100, 200, 300) |
| description | What the cost centre covers |

### counterparties.csv

15 customers and 25 suppliers.

| Column | Meaning |
|---|---|
| counterparty | Company name. This is the key used in the ledger. |
| type | customer or supplier |
| country | Two-letter country code |
| default_account_no | The account this counterparty's invoices are normally booked to |

The key customer is **Nordvik Maskinfabrik A/S** with 20 % of budgeted revenue. Seven customers are Danish (domestic revenue, 55 %) and eight are foreign (export revenue, 45 %).

### budget.csv

One row per account, cost centre and month (22 combinations × 24 months = 528 rows). There is no transaction-level budget.

| Column | Meaning |
|---|---|
| period | Month, `YYYY-MM` |
| account_no | Account |
| cost_centre | Cost centre |
| amount_dkk | Budgeted amount, ledger sign |

### gl_transactions.csv

One row per general ledger line (about 2,100 lines).

| Column | Meaning |
|---|---|
| line_id | Running line number, 1, 2, 3 ... in posting date order |
| voucher_no | Voucher (bilag) number. Usually one line per voucher. The energy correction in event 3 is one voucher with three lines. |
| posting_date | Date, `YYYY-MM-DD` |
| period | Month the line belongs to, `YYYY-MM` |
| account_no | Account |
| cost_centre | Cost centre |
| counterparty | Customer or supplier name. Empty for payroll, card payments and expense claims. |
| description | Bookkeeping text, e.g. `Invoice 10234, pump components` or `Payroll September 2026, production` |
| amount_dkk | Amount, ledger sign |

### planted_events.csv (answer key)

| Column | Meaning |
|---|---|
| event_id | 1 to 6 |
| description | What was planted, in plain language |
| accounts | Account(s) where the event should show as a material variance, separated by `;` |
| cost_centre | Cost centre |
| periods | Months where the event should be material, separated by `;` |
| expected_direction | `unfavourable` or `favourable`. If the direction changes, one value per period, in the same order. |
| approximate_size_dkk | The planted effect per period, in ledger sign, rounded to DKK 1,000. For event 5 it is the total of both accounts. |
| check_basis | `budget` or `flexed budget`: what the event is checked against (see section 7) |

## 5. How the budget is made

1. **Revenue.** Annual budget revenue is divided by 12 and multiplied by a seasonal factor. The seasonal factors are lower in July (0.75, summer shutdown) and December (0.85, holidays). They are rescaled so they average 1, so the year still adds up to the annual budget. Revenue is split between domestic and export by the customers' shares.
2. **Cost of materials (45 % of revenue).** Modelled as **volume × unit cost**. Volume = revenue ÷ selling price per unit (DKK 2,500). Unit cost for raw materials = 2,500 × 45 % × 89 %; for packaging 2,500 × 45 % × 11 %. Materials therefore follow the seasonal pattern of sales.
3. **Staff costs (30 % of revenue).** Annual amount spread evenly over 12 months. Split into wages 80 %, pension and social costs 13 %, overtime 4 %, temporary staff 3 %. Wages and pension are split over cost centres 62 % Production, 16 % Sales, 22 % Administration.
4. **Other operating expenses (13 % of revenue).** Annual amount spread evenly over 12 months, split by account as set in the config (e.g. energy 22 %, repairs 20 %, rent 15 %).

## 6. How the actuals are made

For each account, cost centre and month, the generator starts from the budget and adds small random noise. It then splits the monthly amount into realistic ledger lines. Planted events are added on top.

- **Revenue** is generated per customer: the customer's share of the budget times noise. Each customer gets one to three invoices a month.
- **Volume factor.** Actual revenue divided by budget revenue gives the month's actual sales volume compared with budget. Raw materials and packaging are multiplied by this factor. **When revenue falls, materials fall too.**
- **Noise.** Each monthly amount is multiplied by (1 + a random number). Steady accounts (revenue, materials, payroll, energy) use a standard deviation of 1 %, so they rarely cross the threshold. Lumpy accounts use more: repairs 40 %, IT 40 %, marketing 50 %, travel 50 %, other external costs 50 %. A repair bill or trade fair really does move a lot from month to month. As a result, normal months have roughly 1 to 3 material variances caused by noise alone. They have no story behind them, which tests whether the AI invents explanations. Rent is fixed and has no noise.
- **Noise on costs is timing, not overspend.** For each cost account and fiscal year, the generator draws 12 monthly swings and then subtracts their average. A high month is offset by lower months. Swings are capped at ±75 % before this step. The cap is the same on both sides, so it adds no bias, and a cost can never turn negative.
- **Annual drift.** Each cost account and fiscal year then gets one small shift for the whole year. It is drawn from a normal distribution with a standard deviation of 2 % (`annual_drift_sd`), capped at ±5 %. A year with +2 % drift lands about 2 % over budget. The result looks like a real budget year: most accounts end within a few per cent of budget, none exactly on it. Rent stays fixed. Revenue and energy keep simple month-by-month noise of 1 %, which is too small to add up to anything meaningful over a year.
- **Ledger lines.** The monthly amount is split into a set number of invoices (e.g. 10 for raw materials) of random size that add up exactly. Each line gets a supplier and a description from the config. Payroll is one line per cost centre, booked on the last day of the month, with no counterparty.
- **Energy** is invoiced quarterly and normally booked as one third of the invoice per month, all with the same invoice number.
- **Fixed random seed** (42). Running the generator again produces exactly the same data.

## 7. Planted events

Six events are planted in the actuals. Each one is material in the listed months. The answer key is written to `data/truth/planted_events.csv`. The descriptions in the ledger look like normal bookkeeping text and do not reveal the answer.

| # | Event | Account / cost centre | Months | Effect |
|---|---|---|---|---|
| 1 | Raw material price increase of 8 %, persistent | 2010 Raw materials, Production | Jun to Sep 2026 | Unfavourable, about DKK 0.25 to 0.35m a month |
| 2 | One-off machine repair, one supplier invoice | 4010 Repairs and maintenance, Production | Sep 2026 | Unfavourable, DKK 350,000 |
| 3 | Quarterly energy invoice booked in full in July, corrected in August | 4020 Energy, Production | Jul and Aug 2026 | Jul unfavourable, Aug favourable, about DKK 0.58m each |
| 4 | Key customer cuts volume by 25 % | 1010 Product revenue domestic, Sales | Jul to Sep 2026 | Unfavourable, about DKK 0.4 to 0.5m a month |
| 5 | Sick leave covered by overtime and temporary staff | 3020 Overtime and 3030 Temporary staff, Production | Aug and Sep 2026 | Unfavourable, about DKK 0.1m + 0.2m a month |
| 6 | Unexplained overspend from many small purchases | 4090 Other external costs, Administration | Sep 2026 | Unfavourable, about DKK 120,000 |

How each one looks in the ledger:

1. **Raw material price increase.** All raw material invoices from June 2026 are 8 % higher. There is no special text; the invoices look normal.
2. **Machine repair.** One invoice from Hydra-Service Danmark ApS: `Invoice 48213, emergency repair hydraulic press line 2, parts and labour`.
3. **Energy misposting.** In July the whole Q3 invoice is booked (`electricity and gas Q3 2026`). In August one voucher reverses it and books July and August correctly. September is normal. Over the quarter the total is right; only the timing is wrong.
4. **Key customer volume cut.** Invoices to Nordvik Maskinfabrik A/S are 25 % smaller from July 2026. Lower volume also reduces raw materials and packaging. For packaging this effect alone is below the threshold.
5. **Sick leave.** Overtime is about DKK 100,000 higher, and there are four extra weekly agency invoices for temporary staff of about DKK 200,000 in total. Wages are unchanged, because sick pay is still paid.
6. **Unexplained overspend.** 25 extra small lines (a few thousand DKK each) with generic texts like `Card payment` or `Expense claim` and no counterparty. Normal months contain the same kind of lines, so nothing in the data points to a single cause. **This is a test case: the right answer is that the data shows no clear cause.**

### Events that overlap: why event 1 uses a flexed budget

From July 2026 events 1 and 4 hit raw materials at the same time. The price is 8 % higher, but volume is about 5 % lower (the key customer is 20 % of revenue and cuts 25 %). Against the plain budget, raw materials are then only about 2 to 4 % over budget, which is below the threshold. The price increase is still there; it is hidden by the volume drop.

This is what a controller sees in real life. It is solved with a **flexed budget**: the materials budget is scaled to actual sales volume (budget × actual revenue ÷ budget revenue). Against the flexed budget, the 8 % price effect is clearly material in every month from June. `check_data.py` therefore checks event 1 against the flexed budget and shows the plain variance next to it.

## 8. Materiality

A variance is **material** when it is at least **5 % of budget AND at least DKK 50,000** in absolute terms, per account, cost centre and month. Both conditions must be met. A small account can be 50 % over budget without being material; a large account can be DKK 100,000 over budget without being material. The generator does not use this rule; `check_data.py` does.

## 9. Assumptions

All assumptions are in `config/settings.yaml`. The main ones:

| Assumption | Value | Note |
|---|---|---|
| Cost of materials | 45 % of revenue | Calibrated: Danish manufacturing bought goods for about 44-46 % of revenue, of which packaging about 2 % (source below) |
| Staff costs | 30 % of revenue | Own assumption, not calibrated |
| Other operating expenses | 13 % of revenue | Calibrated: purchased services about 13 % of revenue (source below) |
| Budget EBITDA margin | About 12 % | Result of the three above |
| Seasonality | Low in July and December | Illustrative |
| Selling price per unit | DKK 2,500 | Only used to express materials as volume × unit cost |
| Normal noise | 1 % standard deviation, 40-50 % on lumpy accounts | Gives roughly 1 to 3 noise-driven material variances a month; monthly swings cancel out within each fiscal year |
| Annual drift on costs | 2 % standard deviation, capped at ±5 % | Each cost account lands a few per cent from budget for a full year |
| Key customer | 20 % of revenue | |
| Staff costs and other expenses | Flat over the year | No seasonality |
| Holiday pay | Not modelled separately | Danish holiday pay is assumed accrued evenly |

Source for the calibrated cost shares: Danmarks Statistik, "Industriens køb af varer og tjenester" (2014), <https://www.dst.dk/da/Statistik/udgivelser/NytHtml?cid=21577>.

## 10. Checking the data

`scripts/check_data.py` prints:

1. Revenue and EBITDA per fiscal year, actual vs budget.
2. The number of material variances per month, and which ones.
3. For each planted event: whether it is material, in the expected direction, in every expected month.
4. A reconciliation: it reads the monthly totals back from the Excel file and compares them with a fresh sum of the ledger lines.

It also writes `data/check/variance_check.xlsx` with one sheet per raw table, plus:

- `monthly_by_account`: actual, budget, flexed budget, variances and a material flag per account, cost centre and month.
- `monthly_by_group`: actual vs budget per P&L group and month.

## 11. Known limitations

- Monthly noise swings are capped at ±75 % before the year's average is removed, so two months that both hit the cap end up with identical amounts. For example, marketing in February and March 2025 are both DKK 18.380,75.
