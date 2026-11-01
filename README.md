# Variance Cockpit

A budget vs actual dashboard where AI drafts variance comments and a controller reviews them.

> **All data in this project is synthetic.** The company, Odense Demo Manufacturing ApS, and all of its customers and suppliers are fictional. Any resemblance to real companies is coincidental.

Built with [Claude Code](https://claude.com/claude-code).

## Status

Data layer only: a data specification and a synthetic data generator. See [docs/data-spec.md](docs/data-spec.md).

## Getting started (Windows)

```
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python scripts\generate_data.py
.venv\Scripts\python scripts\check_data.py
```
