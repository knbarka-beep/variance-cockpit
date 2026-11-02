# Variance Cockpit

A budget vs actual dashboard where AI drafts variance comments and a controller reviews them.

> **All data in this project is synthetic.** The company, Odense Demo Manufacturing ApS, and all of its customers and suppliers are fictional. Any resemblance to real companies is coincidental.

Built with [Claude Code](https://claude.com/claude-code).

## Status

- Session 1: synthetic data generator and data specification. See [docs/data-spec.md](docs/data-spec.md).
- Session 2: calculation layer in DuckDB SQL views, reconciliation checks and JSON export for the dashboard. See [docs/sql-guide.md](docs/sql-guide.md).
- Session 3: AI draft comments with Gemini, a deterministic figure check and an evaluation against the planted events. See [docs/ai-layer.md](docs/ai-layer.md).
- Session 5 (in progress): static Next.js dashboard in `web/`, not deployed yet. Run it with `cd web`, `npm install`, `npm run dev`.

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

## Limitations

- **The v2 prompt was tuned on the test it is scored on.** v2 was made after the v1 errors were known, so its 13/15 on the planted events is measured on the same events the prompt was adjusted against. It is not an independent test.
- **The v1 and v2 scores are too high: the AI could see the following month.** v1 and v2 gave the model the following month as context. At month-end close that month does not exist yet, so this was look-ahead: a reversal next month (event 3, the energy misposting) or a continuing trend made the cause easier to see than it is in practice. v3a and v3b remove the following month and are the fair comparison.
- **Event 4 (a customer buying less) is missed in July and September.** The customer baseline is the customer's average for the previous 3 months. It is not seasonally adjusted, so in July every customer looks low. By September it includes the customer's own low July and August, so the drop no longer stands out. Fix in the next version: a baseline against the budget, or against the same month last year.
