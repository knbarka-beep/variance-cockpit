"""Check data/ai/month_summaries.csv the way the AI drafts are checked.

  a) Figure check (draft_comments.figure_check): every figure must match a number for THAT month
     in the views: the KPI row (revenue, EBITDA), the P&L groups, and the material variances.
  b) No look-ahead: no later month or year, no "next month", "will continue" and the like.
  c) British spelling, at most 60 words, no Cause/Persistence labels (check_suggestions.text_problems).
  d) One row per month the dashboard shows, and author is filled in.

Exits with code 1 if anything fails. Never reads data/truth/ (draft_comments blocks it).
Run:  .venv/Scripts/python scripts/check_month_summaries.py
"""
import csv
import re
import sys

import duckdb

from check_suggestions import AHEAD_PHRASE, text_problems
from draft_comments import ROOT, figure_check, rows

FILE = ROOT / "data" / "ai" / "month_summaries.csv"


def month_input(con, period):
    """Everything a controller has for this month at close, nothing later."""
    return {
        "kpi": rows(con, "SELECT * EXCLUDE (period_date) FROM v_kpis WHERE basis = 'month' AND period = ?", [period]),
        "groups": rows(con, """SELECT pl_group, actual_dkk, budget_dkk, variance_profit_dkk, variance_pct
                               FROM v_group_month WHERE basis = 'month' AND period = ?""", [period]),
        "material": rows(con, """SELECT account_name, actual_dkk, budget_dkk, flexed_budget_dkk, variance_profit_dkk, variance_pct
                                 FROM v_material_variances WHERE period = ?""", [period]),
    }


def look_ahead(text, period):
    problems = [f"look-ahead phrase '{m.group(0)}'" for m in AHEAD_PHRASE.finditer(text)]
    problems += [f"later year {y}" for y in re.findall(r"\b20\d\d\b", text) if y > period[:4]]
    return problems


def main():
    con = duckdb.connect(str(ROOT / "data" / "variance.duckdb"), read_only=True)
    periods = [r["period"] for r in rows(con, "SELECT period FROM periods ORDER BY period")]
    summaries = list(csv.DictReader(FILE.open(encoding="utf-8")))
    failed = [f"missing month {p}" for p in sorted(set(periods) - {s["period"] for s in summaries})]
    for s in summaries:
        text, p = s["summary"].strip(), s["period"]
        if not text:
            continue
        fc = figure_check(text, month_input(con, p))
        problems = [f"figure not found: {u}" for u in fc["unmatched"]] + look_ahead(text, p) + text_problems(text)
        problems += [] if s.get("author") else ["author is empty"]
        problems += [] if p in periods else ["not a dashboard month"]
        print(f"{p}  {fc['figures_matched']}/{fc['figures_found']} figures  {'OK' if not problems else 'FAIL: ' + '; '.join(problems)}")
        failed += [f"{p}: {x}" for x in problems]
    con.close()
    if failed:
        sys.exit("\n" + "\n".join(failed))
    print(f"all {len(summaries)} month summaries passed")


if __name__ == "__main__":
    main()
