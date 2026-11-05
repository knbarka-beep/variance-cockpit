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

## Prompt B, A4. Private details (check only)

- Done earlier in this session (history rewritten to the noreply address, employer name removed). Rerun of the check:
  `git log --all --format='%ae %ce' | sort -u` shows only `299253900+knbarka-beep@users.noreply.github.com`. 0 hits for
  the old address and 0 for "Ria" as a word, in tracked files and in the full history. No absolute personal paths in tracked
  files. No key or token patterns (Google `AIza`, `sk-`, `sk-ant`, `ghp_`, `api_key=`) and no `.env` file in any commit.

## Prompt B, A5. README, final pass

- Rewritten in the order of the brief. About 1.040 words counting the code block and link syntax; under 1.000 in prose.
- Every number checked against the files: 2.120 ledger lines (`gl_transactions.csv`), 71 material variances, 7 checks,
  v3a 12 of 15, 5 of 55, 71 of 71, 70 of 71 within 60 words, 1 sign error (`evaluation.json`); v1 10 and v2 13 of 15;
  v3b 16 of 71 (the earlier README; `evaluation.json` still holds an older v3b run of 10 drafts, not rerun); review 35/30/6
  and 16 of 18 (`reviews.csv`, A1); Sep 2026 EBITDA 0,25m against 1,55m (`kpis.json`).
- The README says "material variance", the project's own term, instead of "significant", which is on the style ban list.
  The dashboard still says "Significant variances"; not changed, to keep this a text-only step.
- Removed the step-by-step command blocks for the review scripts and the session list; they are in `docs/ai-layer.md`
  and the git history. Kept a short build block. Kept every limitation; added "one run per prompt version".
- The screenshot path `docs/screenshots/desktop-light.png` is created in A8.

## Prompt B, A6. Case sheet

- `docs/case-sheet.md`, about 330 words, linked from the README.
- The brief's "marketing 41 % over budget" figure is not in the repo or its history (only the fix is: monthly swings
  centred per fiscal year, `docs/data-spec.md`). The case sheet describes the finding without the number. Knut can add it
  if he has the figure from his own Excel check.
- September drivers are taken from `v_material_variances` and the bridge: revenue 0,51m, raw materials price 0,37m,
  temporary staff, overtime and the repair invoice.

## Prompt B, A7. Private drafts

- `private/cv-line.md` (three lines, 23 to 25 words) and `private/pitch.md` (English 83 words, Danish 74, spoken 75)
  written; both gitignored, not committed. No video script. Skill levels not upgraded: the CV lines say what was built,
  not how well Knut knows Python or SQL.

## Prompt B, A8. Ready for Vercel, and QA

- **Data on Vercel.** With `web/` as root directory, `../data/export` is not part of the build. Chosen: commit the copied
  export, `web/lib/dashboard.json` (about 290 KB), and let `prepare-data.mjs` skip the copy when `../data/export` is missing.
  Locally every `npm run build` still refreshes it from `data/export`, so the rule is: build locally, then commit
  `dashboard.json` with the data change. Not chosen: Vercel's "include files outside the root directory" setting, because
  the site would then depend on a project setting that is easy to miss.
- Tested by copying only the tracked files of `web/` to a folder outside the repo, `npm ci` and `npm run build`: the build
  used the committed file and succeeded, with `og.png` and `404.html` in the output.
- **Metadata.** Title "Variance Cockpit (fictional data)", a meta description that says the data is synthetic, Open Graph and
  Twitter card with `web/public/og.png` (a 1200 x 630 screenshot of September 2026). `metadataBase` comes from Vercel's
  `VERCEL_PROJECT_PRODUCTION_URL`, so the image link is absolute on the live site; locally it falls back to localhost.
- **Footer.** Links to the method page on GitHub and to the repo. `docs/method-draft.md` lost its "draft, not linked"
  banner, because it is now linked. The file name is kept so older links still work.
- **404 page.** New `web/app/not-found.tsx`, so "(fictional)" is visible on every page, not only the dashboard.
- **Full data flow.** `generate_data.py` (data/raw unchanged afterwards, same seed), `check_data.py`, `build_db.py` (7 of 7
  checks), `test_draft_comments.py`, `test_review.py`, `check_suggestions.py` (71, 0 failed), `check_month_summaries.py`
  (24 passed), `npm test` (4 passed), `tsc`, `eslint`, `npm run build`: all pass. `evaluate_ai.py` was not rerun: it would
  rewrite `data/ai/evaluation.json`, which this run must not change.
- **QA in headless Edge**, 17 of 17: the B3 figures for September 2026, 16 of 18 and 35 + 30 + 6 = 71 on the panel,
  "Draft summary (Claude)", no "not reviewed" in any of the 24 months, Tab reaches the bridge buttons, the variance list
  and the drill-down, a visible focus ring on every stop, no horizontal scroll at 375 px, "(fictional)" on the 404 page,
  no console errors. Two first-run failures were test bugs (upper-case CSS and the test server's own 404 page).
- **Screenshots** in `docs/screenshots/`: desktop light and dark, 375 px, drill-down, focus in the drill-down, AI quality panel.

## Prompt B, fixes before going public (Knut's instructions)

- README and case sheet use "significant variance", the dashboard's own term ("Significant variances"). "Material" was
  dropped earlier because it is confused with raw materials. The style ban is on "significant" as filler, not as the defined
  term. This replaces the A5 choice above.
- Case sheet: marketing about 41 % over budget in FY2025 from a random draw, fixed by centring the noise per year. The 41 %
  comes from Knut's manual Excel check on 01.11.2026, on the data set before the fix. It is not reproducible from the
  current data, which was regenerated after the fix.

## Prompt B, Part B. GitHub and Vercel

- B1: rewritten `main` force-pushed with `--force-with-lease` against the old `ddb1508`; repo made public with a one-line
  description. It had been private, so the old history with the personal email was never public.
- B2: Claude's Vercel connector had no access to the `senor-robot` team (403), so the Vercel CLI was used:
  `project add`, root directory `web` and framework `nextjs` set through `vercel api`, `vercel link`, `vercel git connect`.
  The production deploy came from a push to `main`, which also proves that later pushes deploy automatically.
  Other projects in the team were not touched. `vercel link` created `.env.local` with a short-lived OIDC token; it is
  gitignored by `.env*`.
- B3: live site checked in headless Edge with the same QA script as A8: 17 of 17 pass, including all B3 items.
- B4: live link at the top of the README and as the repo's website.

## Layout fixes after launch

- Bridge and list: the grid now uses `align-items: start`, so each card takes its own height, and the bridge card is
  `position: sticky` (16 px from the top) from 1024 px, where the two cards sit side by side. Below that the cards stack and
  nothing is sticky. Checked in headless Edge for Jun and Sep 2026, filtered and unfiltered, 1280 and 375 px, light and dark:
  51 of 51 checks pass, no console errors.
- Price rows: when an account row has a price-effect sub-row, the account row shows the AI label and status and the
  sub-row shows only the price/volume split and "vs flexed budget". Each row still opens its own draft in the drill-down.
  Counts unchanged against the live site before the change: Jun 2026 list 5, KPI 5; Sep 2026 list 6, KPI 6; panel 35/30/6.
- `data/ai/evaluation.json` still holds an older partial v3b run (10 drafts); the README figure 16 of 71 is from the later run; the file is not shown on the dashboard.

## Design P1: shared kit redesign (05.11.2026)

Unattended run of `../prompts/design-p1.md`. Impeccable's interview step was not run: the prompt says "no questions",
so the brief in the prompt stands in for the interview, and every choice is logged here.

### Step 0. Before screenshots and the selectors the checks rely on

- `scripts/screenshots.mjs` (new, adapted from startup-runway): `before|after` takes the comparison set into
  `docs/screenshots/redesign/`, `qa` runs the click-through checks and retakes `docs/screenshots/`, `qa <url>` checks the live site.
  The earlier A8/B3 QA script was never committed, so this one replaces it with the same checks.
- Selectors and ids it relies on, kept through the redesign: `#period` (month select), buttons named "Previous month" and
  "Next month", `.vrow` (one per list row), `dialog.drill`, `#drill-title`, "Close details", `#ai-title`, `#bridge-title`,
  `#list-title`, `#summary-title`, and from the kit `.info-btn` / `.info-pop`.
- BEFORE on current main (`5b62603`): all figure checks pass. Two "fails" were test bugs (upper-case CSS label; focus
  landing on `<body>` after the last stop) and were fixed in the script. "16 of 18" fails on main as expected: the old
  panel says "agreed with 16"; the redesign shows it as "16 of 18". Focus ring is the old bright blue `#1d4ed8`.

### Step 1. Kit, tokens and accent

- Copied from `../startup-runway/web`: `styles/tokens.css`, `styles/kit.css`, `components/kit/*`, `postcss.config.mjs`;
  Tailwind 4.3.3 installed exactly as the kit README says. Fonts switch from Inter to Source Serif 4 (headings) and IBM Plex Sans.
- Changes to the copied kit, kept small: `CardHeader` takes an `id` (the checks use `#bridge-title`, `#list-title`, `#ai-title`);
  three `eslint-disable-next-line react-hooks/set-state-in-effect` lines in `ThemeToggle` and `useAnimateOnce` (P2 has no ESLint;
  the pattern is intended: read a browser-only setting once after hydration); `postcss.config.mjs` exports a named object (lint).
- Theme: light by default, dark behind the toggle, `?theme=dark|light` works, as in P2. The old page followed the OS setting;
  that is dropped so the three projects behave the same.
- **Accent: deep petrol, `#1F5F6B` light / `#6FB0BB` dark.** Two candidates were measured against the kit tokens:

  | | Light on page / card | Dark on page / card | ΔE to green | ΔE to muted grey | ΔE to P2 ink blue |
  |---|---|---|---|---|---|
  | Graphite slate `#3D4651` / `#9AA6B2` | 9,1 / 9,6 : 1 | 7,4 / 6,9 : 1 | 43 / 44 | **19 / 14** | 25 / 21 |
  | Petrol `#1F5F6B` / `#6FB0BB` | 6,9 / 7,2 : 1 | 7,6 / 7,1 : 1 | 33 / 35 | 25 / 26 | 26 / 24 |

  Both pass AA for text and 3:1 for chart lines in both themes. Slate is too close to the muted text and the grey budget
  line: as the "actual" line in the trend charts and as the focus ring it would read as one more grey, not as an accent.
  Petrol stays clearly apart from the favourable green (hue 189° against 151°), from the red, and from P2's ink blue (teal, not blue).
  `--accent-soft` `#E2EEF0` / `#1A2C30` (accent text 6,1 / 5,9 : 1), `--on-accent` white / `#141412` (7,2 / 7,6 : 1).

### Step 2. Layout (impeccable, Operate mode)

- Order: thin sticky header (name, "(fictional)", month controls, theme) > one caption line on synthetic data with an (i) that holds
  the old yellow notice in full > **hero: EBITDA vs budget for the month** (large serif amount, "below/above budget", red/green pill
  with the %), one sentence with actual vs budget and the two largest significant variances > revenue, EBITDA margin and
  significant variances as compact stats > draft summary (Claude) > bridge (large card, sticky on desktop) beside the variance list
  > AI quality > footer.
- Text moved into (i) popovers, none deleted: the synthetic-data notice, the materiality rule (also still in the footer),
  the metric definitions and the planted-events note with "How this is measured", and the whole review paragraph. The card keeps
  the counts and "agreed with 16 of 18" visible. New popover text only describes what the page shows (what EBITDA adds up from,
  how to read the bridge). There is no separate method page in this project; `docs/method-draft.md` (footer link) has everything in full.
- Bridge filter chips became the kit's segmented control ("All" + the four P&L groups, `aria-pressed`); clicking a bar still filters.
- List rows are separated by hairlines instead of boxed cards (no card inside a card). Unicode ▲/▼ arrows in the list are gone:
  colour plus the word "favourable/unfavourable" carry the direction. Month arrows and the close button are drawn SVG, not ‹ › ✕.
- Totals in the bridge use `--neutral` (warm grey), budget lines dashed `--neutral`, actual lines `--accent`.
- Impeccable rules used: Operate mode (familiar patterns, restrained colour, accent only for focus, selection and the actual line);
  craft floor: no eyebrow above a heading (the kit's `eyebrow` prop is not used; small labels name values, not headings), no nested
  cards, no unicode glyphs as icons, browser surfaces themed (focus ring, `::selection`, tabular figures), one authored motion
  moment (the bars rising once); "Refinement preserves": all copy, figures and behaviour kept. The detector
  (`impeccable detect`) found no issues in `web/app`, `web/components`, `web/styles`.
- Motion: 150 ms hover/focus/segmented, 150 ms popover, 200 ms drill-down slide-in, bars rise once in 400 ms through a CSS class
  that is removed after 500 ms. Recharts' own animation is not used because it hides the value labels until it ends.

### Loop rounds

1. Bar value labels were missing in the light screenshot (Recharts hides labels while it animates, exactly what the brief warns
   about): moved the load animation to CSS so the numbers are always drawn. "vs budget DKK 10,76m" wrapped over three lines in the
   revenue stat: budget moved to its own line. The header ran off the screen at 375 px: controls wrap under the title on a phone.
   Removed an unnamed tab stop on the revenue mini chart.
2. The hero sentence was hard to read (commas in account names next to the amounts): amounts in parentheses, the % dropped from the
   sentence because the pill shows it. A third round would only be polish, so the loop stopped here.

### Checks

- Data flow: `generate_data.py`, `check_data.py` (totals match), `build_db.py` (all `v_checks` pass), `check_suggestions.py`
  (71, 0 failed), `check_month_summaries.py` (24 passed), `test_draft_comments.py`, `test_review.py`, `npm test` (4 passed),
  `tsc`, `eslint`, `npm run build`: all pass. Only change in `data/`: the `built_at` timestamp in `meta.json`, reverted.
  `web/lib/dashboard.json` is byte-identical, so every figure on the page is the same. `evaluate_ai.py` not rerun (it would rewrite
  `data/ai/evaluation.json`). `data/truth/` not read.
- `node scripts/screenshots.mjs qa`: 25 of 25 pass (figures, 35 + 30 + 6 = 71, "16 of 18", no "not reviewed" in 24 months, Tab
  order, focus ring in the accent, drill-down Enter/Esc, popovers Enter/Esc and focus back, 375 px no sideways scroll, reduced motion,
  no console errors).
- Compare images: `docs/screenshots/redesign/compare-*.png`. `web/public/og.png` recropped (1200 x 630) from `desktop-light-after.png`.
- `docs/screenshots/focus-drilldown.png` removed: not referenced anywhere and it showed the old design.
