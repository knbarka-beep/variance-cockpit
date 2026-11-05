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

Result: `data/check/spot_check_sample.csv`, committed alone in b176b87
("Pre-register spot-check sample (seed 20261105)", 2026-11-05 15:57 +0100). The commit was first 23722ed; the
email rewrite on the same day (see step 6) gave every commit a new hash. Date, message and file content are unchanged
(file blob 105a432 in both). `data/check/` is gitignored, so the file was added with
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

## 3. Claude's statuses applied as the review

- Used a small new script, `scripts/apply_suggestions.py`, not `review_import.py`: the import reads the controller's own
  columns in `review.xlsx`, which are empty, and the brief says not to touch `review.xlsx`.
- `reviewer_note` holds Claude's "why suggested" text, so the reason is visible on the dashboard.
- New column `reviewed_by` (`claude` / `knut` / empty). `check_reviews` (used by `build_db.py`) now also rejects any other value,
  and a status without `reviewed_by` or the other way round. Two new cases in `test_review.py`.
- `review_import.py` marks imported rows with a status as `knut`. Note: running it now would overwrite Claude's statuses with
  the empty controller columns from `review.xlsx`; it is meant for a full review by Knut, not for the spot check.
- Dashboard: status reads e.g. "Approved (suggested by Claude)" or "(checked by Knut)"; the drill-down heading is now "Review", not "Controller review".

## 4. Month summaries (drafts by Claude)

- One sentence for each of the 24 months the dashboard shows (2024-10 to 2026-09), `author = claude-draft`.
- Written from the views for that month only: KPI row, P&L groups and material variances, plus the reviewed comments for
  drivers (for example "mostly Nordvik Maskinfabrik A/S" comes from Claude's suggested comments, two of which are in Knut's sample).
- Only amounts are cited for EBITDA, not percentages: with a budget near zero (July) the percentage is meaningless (-730 %).
- New check script `scripts/check_month_summaries.py` reuses `draft_comments.figure_check` and `check_suggestions.text_problems`.
  Input per month = that month's KPI row, P&L groups and material variances; nothing later. All 24 pass (62 figures).
  A wrong figure (DKK 0,99m) and "will continue in 2027" were tried and caught.
- The check does not verify "over"/"under" or "third month in a row"; I checked those by hand against `v_material_variances`.
- Honest note: earlier in this same session I read `config/settings.yaml`, whose `events` section describes the planted
  events (the same information as the answer key, in config form). I did not read `data/truth/`. The summaries only say what
  the views and ledger texts show, but they were not written blind.
- Dashboard: the card reads "Draft summary (Claude)" when `author = claude-draft`, otherwise "Controller's summary".

## 5. Method and panel text

- `docs/method-draft.md` (still a draft, not linked), the AI quality panel and the README limitation now describe the
  three steps: Gemini drafts, Claude suggests statuses with written rules, Knut checks a pre-registered sample of 18.
  Agreement is the placeholder "[x of 18]" in all three places until Knut has filled in the sheet.
- Added to the limitations: the sample over-weights rejected rows, so it is not a direct estimate for all 71; and even
  16 of 18 would give a wide 95 % interval (about 67 % to 97 %, Wilson). The 53 unsampled rows carry Claude's status only.
- Disclosed in the method draft that this session also saw the event settings in `config/settings.yaml` (see step 4).
- Panel metric notes changed from "used as written / changed by the controller / rewritten" to the status rules,
  because no controller has changed them yet.
- README first line no longer says "a controller reviews them"; it says what actually happens.

## 6. Prep for deploy

- UI test in headless Edge over the DevTools protocol, with a small Node script in the session scratchpad (no new
  dependency such as Playwright). 15 of 15 checks passed: month summary label and text for all 24 months, statuses
  "(suggested by Claude)" in the list, drill-down with review block and Claude's reason, Esc closes it, Tab reaches the
  controls and rows with a visible outline on every focused element, Enter opens a row, dark mode, no horizontal scroll at 375 px
  (page and drill-down). Four first-run failures were bugs in the test script (wrong selector for the native `<dialog>`,
  upper-case headings, Enter without a key text), not in the dashboard.
- `.gitignore`: added `.env*` (was only `.env`) and `private/`; `data/check/` became `data/check/*` with an exception for
  `spot_check_sample.csv`, so the pre-registration is visibly meant to be public. `review.xlsx` and `spot_check.xlsx` stay ignored.
- Safety scan of the full git history (all branches): no keys, tokens or `.env` files ever committed; no absolute personal
  paths; no phone numbers; no thesis, ECIT or coursework references. Two findings, history not rewritten:
  1. Every commit's author email was a personal address. Fixed on 2026-11-05: history rewritten to the GitHub noreply address.
  2. `CLAUDE.md` (committed) named the author's employer in the rule that forbids using anything from it. Fixed on 2026-11-05: rephrased to "the author's employer", also in the history.

## Prompt B, A1. Knut's spot check imported

- Result read from `data/check/spot_check.xlsx`: **16 of 18 agree**, above the 14 threshold. All 6 rejected agreed.
- Disagreements:
  - 2025-02_4010_Production: Claude approved, Knut edited. ElektroTeknik Tarup ApS rose about DKK 58k and offsets almost all
    of the Hydra-Service drop; the draft misses it.
  - 2026-09_3030_Production: Claude edited, Knut approved. Driver and share are right, August and September are both over,
    and American spelling alone is not a reason to edit under the status rules.
- New script `scripts/import_spot_check.py` (rerunnable): sets `reviewed_by = knut` on all 18 rows and writes Knut's status,
  final comment and note for the two disagreements. Knut's notes were in Norwegian; the English final comment and notes in
  the script are the ones given in the brief. The script stops if the sheet's disagreements differ from the ones in the script.
- The new final comment for 2025-02_4010 passed the same checks as Claude's suggestions (figures, look-ahead, spelling,
  60 words) with no change to the numbers. `build_db.py`: all 7 checks pass.
- Status counts are unchanged at 35 approved, 30 edited, 6 rejected (one row moved each way), 71 in total, 18 by Knut.
- `review_import.py` was not run.

## Prompt B, A2. Month summary for Feb 2025

- Nothing changed. The sentence only says repairs and maintenance was DKK 0,10m under budget; it names no supplier, so it
  does not repeat the missed driver. Still `author = claude-draft`; `check_month_summaries.py` still passes.

## Prompt B, A3. Agreement filled in

- "[x of 18]" replaced with 16 of 18 in the method page, the AI quality panel and the README, with the two disagreements
  in one line each and the note that one went each way and 18 cases are too few to say whether Claude leans either way.
- The panel's agreement sentence is fixed text, not computed: the sheet is not part of the build. The status counts are
  computed from `reviews.csv`: 35 + 30 + 6 = 71, matching the file; 18 rows by Knut, 53 by Claude.
- Method page now says `config/settings.yaml` was read after the statuses were written (it was read in the same session,
  after `review_suggestions.py` had been committed). Note: decisions steps 1 and 5 above still describe the placeholder as it
  was then; they are history and left as written.
