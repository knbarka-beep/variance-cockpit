# Method (draft, not yet reviewed)

> Draft for review. Not linked from the README or the dashboard yet.

## The data

All data is synthetic. Odense Demo Manufacturing ApS is a fictional manufacturer with about DKK 120m in revenue, 80 employees and three cost centres. The data covers October 2024 to September 2026, with a profit and loss statement down to EBITDA.

A Python script builds a monthly budget per account, then the actuals: budget plus random noise, split into ledger lines with suppliers, customers and invoice texts. The main cost shares are calibrated to Danish manufacturing statistics (Danmarks Statistik): materials about 45 % of revenue, purchased services about 13 %. Staff costs are my own assumption. Lumpy accounts such as repairs, IT and marketing get much more noise than steady ones, as in real life. The monthly swings cancel out over each fiscal year, so they are timing, not overspend. A fixed random seed makes every run identical.

Six business events are planted on top: a price increase, a customer buying less, an invoice booked in the wrong month and corrected later, a one-off repair, extra staff costs, and an overspend with no clear cause. The ledger texts look like normal bookkeeping. An answer key records the events; only the evaluation script reads it.

## Materiality

A variance is material when it is at least 5 % of budget and at least DKK 50.000, per account, cost centre and month. The percentage stops large accounts from flagging small noise; the amount stops small accounts from flagging trivial sums. A normal month then has a few material variances, which a controller can actually read.

## Flexed budget for raw materials

When sales volume falls, raw material costs fall with it, and a price increase can hide behind the lower volume. Raw materials therefore also get a price row: actual cost against the budget scaled to actual sales volume. What remains is a price or usage effect. The ledger has no quantities, so it cannot say which.

## The AI layer

For each material variance the model (Gemini) receives the actual, budget and variance, the largest ledger lines, each supplier's or customer's change against its own three-month average (raw materials use the flexed budget instead), and the three previous months. It never sees later months: at month-end close the future does not exist. It returns a short comment, a cause category and a view on persistence.

A check without AI compares every figure in the comment with the input. All drafts are written in advance and stored; the dashboard never calls the AI.

## Evaluation

The drafts are scored against the answer key. For the version in the dashboard (v3a):

- Planted events: right cause category in 12 of 15 event months.
- Noise variances (no event behind them): 5 of 55 drafts claim a price effect, a lasting trend, or a supplier or invoice that is not behind the variance.
- Figure check: 71 of 71 drafts pass.

This is one run. The model does not answer the same way every time, so another run could score differently; the spread has not been measured. The scores measure categories, not how well a comment is written.

## Review

Three steps, by three different reviewers:

1. **Gemini wrote the drafts** (v3a, `gemini-3.5-flash-lite`).
2. **Claude, a different model, suggested a status for all 71** (approved, edited or rejected) and a new text where needed, using written rules: rejected when the draft claims something wrong, edited when it is right but misses the driver or context, approved when it is right as written; plus rules for when "one-off", "too early to tell" or "persistent" fit. Claude used the ledger, the budget and months up to the one commented on. A script checks Claude's figures and wording the same way the drafts are checked. Result: 35 approved, 30 edited, 6 rejected. These statuses are what the dashboard shows, marked "suggested by Claude".
3. **I checked a pre-registered random sample of 18**: all 6 rejected, plus 6 edited and 6 approved drawn at random (Python, seed 20261105). The sample and the rule for reporting were committed before I looked at any row. Agreement: **[x of 18]**. Where I disagree, my verdict replaces Claude's and the row is marked "checked by Knut".

The review is not blind. Claude saw the drafts and the ledger, and read the table of planted events in `docs/data-spec.md` only after writing the suggestions; in a later session it also saw the event settings in `config/settings.yaml` before drafting the month summaries. I know how the synthetic data was made.

Limitations: one model grading another is not the same as human review, and 18 is a small sample. Even 16 of 18 would leave a wide margin (a 95 % interval of roughly 67 % to 97 %). The sample also over-weights rejected rows (all 6 are in it), so it is not a direct estimate for all 71. The 53 rows outside the sample carry Claude's status only.

The month summaries on the dashboard are drafts by Claude, labelled as such. Their figures are checked against that month's numbers by the same script logic.

## What the tool cannot do

- See causes that are not in the ledger, such as a customer call or a decision in a meeting.
- Tell price from usage on raw materials.
- Know whether a variance will continue. In the first month it can only say it is too early to tell.
- Prove itself on real data. It has only been tested on synthetic data with known events.
