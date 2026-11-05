# Decisions

Choices made during the unattended session of 2026-11-05 (Claude, following the brief in the project chat).
Newest at the bottom.

## 1. Spot-check sample, pre-registered

Fixed before Knut looks at any row, and before the spot-check sheet existed.

**Sample.** All 6 rows Claude suggested as rejected, plus 6 random edited and 6 random approved = 18.
Python `random.Random(20261105)` (seed = today's date), drawn from the ids in
`scripts/review_suggestions.py` sorted alphabetically per status, edited drawn before approved:

```python
rng = random.Random(20261105)
by = {s: sorted(v for v, t in S.items() if t[0] == s) for s in ("approved", "edited", "rejected")}
edited, approved = rng.sample(by["edited"], 6), rng.sample(by["approved"], 6)
```

Result: `data/check/spot_check_sample.csv`, committed alone in 23722ed
("Pre-register spot-check sample (seed 20261105)"). `data/check/` is gitignored, so the file was added with
`git add -f`; the .gitignore was not changed in that commit, to keep it alone.

**Rule (fixed now, not changed after the result is seen).**

- Knut marks *Agree* yes or no per row.
- Agreement is reported as *x of 18*, and every disagreement is listed (variance id, Claude's status, Knut's status, Knut's note).
- Knut's verdict replaces Claude's status for those rows, and `reviewed_by` becomes `knut` for all 18 checked rows.
- If agreement is below 14 of 18, the dashboard says so plainly, and the project is not deployed until it has
  been discussed in the project chat.
- The 53 rows outside the sample keep Claude's status with `reviewed_by = claude`, and the dashboard says so.

## 2. Spot-check sheet

- New script `scripts/spot_check_export.py` writes `data/check/spot_check.xlsx` (gitignored with the rest of `data/check/`).
  It reuses `build_input` from `draft_comments.py`, so Knut sees the same numbers the AI saw, and the same guard against `data/truth/`.
- Rows are sorted by variance id (period first), not grouped by Claude's status, so the order follows the calendar.
- Added two columns beyond the brief: each counterparty's amount against its own 3-month average (top 3), and the
  previous three months' variance. Without them the rows about "third month in a row" or "Nordvik invoiced less than in June"
  cannot be checked from five ledger lines alone.
- Ledger amounts are shown with revenue and costs as positive numbers; the variance column is profit view (+ = favourable).
- The instruction box is one merged cell at the top; header and box are frozen together, because Excel can only freeze from the top.
- No formulas. The script refuses to overwrite a sheet where any blue column is filled in.
