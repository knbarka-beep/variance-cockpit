# Variance Cockpit

A budget vs actual dashboard where AI drafts variance comments and a controller reviews them.

> **All data in this project is synthetic.** The company, Odense Demo Manufacturing ApS, and all of its customers and suppliers are fictional. Any resemblance to real companies is coincidental.

Built with [Claude Code](https://claude.com/claude-code).

## Status

- Session 1: synthetic data generator and data specification. See [docs/data-spec.md](docs/data-spec.md).
- Session 2: calculation layer in DuckDB SQL views, reconciliation checks and JSON export for the dashboard. See [docs/sql-guide.md](docs/sql-guide.md).
- Session 3: AI draft comments with Gemini, a deterministic figure check and an evaluation against the planted events. See [docs/ai-layer.md](docs/ai-layer.md).

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
