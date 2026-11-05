# Variance Cockpit

A budget vs actual dashboard where AI (Gemini) drafts variance comments, a second model (Claude) suggests a review status for each, and a controller checks a pre-registered sample of those statuses.

> **All data in this project is synthetic.** The company, Odense Demo Manufacturing ApS, and all of its customers and suppliers are fictional. Any resemblance to real companies is coincidental.

Built with [Claude Code](https://claude.com/claude-code).

## Status

- Session 1: synthetic data generator and data specification. See [docs/data-spec.md](docs/data-spec.md).
- Session 2: calculation layer in DuckDB SQL views, reconciliation checks and JSON export for the dashboard. See [docs/sql-guide.md](docs/sql-guide.md).
- Session 3: AI draft comments with Gemini, a deterministic figure check and an evaluation against the planted events. See [docs/ai-layer.md](docs/ai-layer.md).
- Session 5: static Next.js dashboard in `web/`, not deployed yet. See [Dashboard](#dashboard-local-build) below.

## Getting started (Windows)

```
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python scripts\generate_data.py
.venv\Scripts\python scripts\check_data.py
.venv\Scripts\python scripts\build_db.py
```

AI draft comments (needs `GEMINI_API_KEY` in `.env`; see [docs/ai-layer.md](docs/ai-layer.md)):

```
.venv\Scripts\python scripts\draft_comments.py --dry-run
.venv\Scripts\python scripts\draft_comments.py
.venv\Scripts\python scripts\build_db.py
.venv\Scripts\python scripts\evaluate_ai.py
```

Controller review in Excel (see [docs/ai-layer.md](docs/ai-layer.md#the-controllers-review)):

```
.venv\Scripts\python scripts\review_export.py
rem fill in status, final_comment and reviewer_note in data\check\review.xlsx, then:
.venv\Scripts\python scripts\review_import.py
.venv\Scripts\python scripts\build_db.py
```

## Dashboard (local build)

The dashboard in `web/` is a static Next.js site (Recharts, no server, no live AI). It reads only `data/export/` (written by `build_db.py`) and the aggregate scores in `data/ai/evaluation.json`; `web/scripts/prepare-data.mjs` copies the fields it needs into `web/lib/dashboard.json` before every build.

```
.venv\Scripts\python scripts\build_db.py
cd web
npm install
npm run dev     # http://localhost:3000, rereads data/export on start
npm run build   # static site in web\out
npm test        # number format and grouping rules
```

## Limitations

- **The v2 prompt was tuned on the test it is scored on.** v2 was made after the v1 errors were known, so its 13/15 on the planted events is measured on the same events the prompt was adjusted against. It is not an independent test.
- **The v1 and v2 scores are too high: the AI could see the following month.** v1 and v2 gave the model the following month as context. At month-end close that month does not exist yet, so this was look-ahead: a reversal next month (event 3, the energy misposting) or a continuing trend made the cause easier to see than it is in practice. v3a removes the following month. v3b was planned as the fair comparison with only the model changed, but it stopped at 16/71 drafts because of 503 errors and then the free-tier quota at the provider.
- A comparison with a stronger model (gemini-3.6-flash, v3b) was started but stopped at 16/71 drafts because of server errors and the free-tier quota at the provider. The dashboard uses v3a.
- **The review is mostly by a model, and not blind.** Claude suggested the status for all 71 drafts using written rules; I checked a pre-registered random sample of 18 (all 6 rejected, 6 edited, 6 approved; rule in [docs/decisions.md](docs/decisions.md)). Agreement: [x of 18]. One model grading another is not human review, and 18 is a small sample. Claude saw the drafts and the ledger, and read the planted-events table only after writing the suggestions; I know how the data was generated. The month summaries on the dashboard are drafts by Claude.
- Some drafts that the evaluation counts as false 'persistent' claims are reasonable readings of the ledger at close, because the noise in the synthetic data evens out over the year, which a controller could not know. The measure was fixed before the runs and has not been changed.
- **Event 4 (a customer buying less) is missed in July and September.** The customer baseline is the customer's average for the previous 3 months. It is not seasonally adjusted, so in July every customer looks low. By September it includes the customer's own low July and August, so the drop no longer stands out. Fix in the next version: a baseline against the budget, or against the same month last year.
