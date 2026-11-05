"""Build the DuckDB calculation layer and export JSON for the dashboard.

Steps:
  1. Run check_data.py (the independent pandas check) to get its material counts.
  2. Create data/variance.duckdb from scratch, with a params table from config/settings.yaml.
  3. Run every sql/*.sql file in number order. All calculations live there.
  4. Run the reconciliation checks (view v_checks). Stop with an error if any fails.
  5. Export the views as JSON to data/export/.

Python only runs SQL and writes files; it calculates nothing itself.
This layer never reads data/truth/.

Run from the project folder:  .venv/Scripts/python scripts/build_db.py
"""
import json
import os
import subprocess
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import duckdb
import yaml

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)  # the SQL files use paths relative to the project folder
cfg = yaml.safe_load(Path("config/settings.yaml").read_text(encoding="utf-8"))
DB = Path("data/variance.duckdb")
EXPORT = Path("data/export")

# 1. Independent check. It writes data/check/material_counts.csv, which check 6 compares against.
subprocess.run([sys.executable, "scripts/check_data.py"], check=True, capture_output=True)

# 2. Fresh database with the parameters from the config (nothing hard-coded in SQL).
DB.unlink(missing_ok=True)
con = duckdb.connect(str(DB))
con.execute(
    """CREATE TABLE params AS SELECT
         CAST(? AS VARCHAR)       AS company_name,
         CAST(? AS DOUBLE)        AS materiality_pct,
         CAST(? AS DECIMAL(18,2)) AS materiality_min_dkk,
         CAST(? AS INTEGER)       AS fiscal_year_start_month""",
    [cfg["company"]["name"], cfg["materiality"]["min_pct"], cfg["materiality"]["min_amount_dkk"],
     cfg["period"]["fiscal_year_start_month"]])
con.execute("""CREATE TABLE check_data_counts AS
               SELECT * FROM read_csv('data/check/material_counts.csv', header = true,
                                      columns = {'period': 'VARCHAR', 'material_count': 'INTEGER'})""")

# AI drafts and reviews are optional: before the first AI run, start from empty files.
Path("data/ai").mkdir(parents=True, exist_ok=True)
if not Path("data/ai/drafts.json").exists():
    Path("data/ai/drafts.json").write_text("[]\n", encoding="utf-8")
if not Path("data/ai/reviews.csv").exists():
    Path("data/ai/reviews.csv").write_text("variance_id,status,final_comment,reviewer_note,reviewed_by\n", encoding="utf-8")
# One summary sentence per month, written by the controller in the review (not by AI). Empty = not shown.
if not Path("data/ai/month_summaries.csv").exists():
    Path("data/ai/month_summaries.csv").write_text("period,summary\n", encoding="utf-8")
# Same status rules as review_import.py: stop before building on a bad review file.
sys.path.insert(0, str(Path(__file__).parent))
from review_import import check_reviews, read_csv  # noqa: E402
if problems := check_reviews(read_csv()):
    sys.exit("data/ai/reviews.csv has review errors - nothing built:\n  " + "\n  ".join(problems))

# 3. All calculations: the SQL files, in order.
for sql_file in sorted(Path("sql").glob("*.sql")):
    con.execute(sql_file.read_text(encoding="utf-8"))
    print(f"ran {sql_file}")

# 4. Reconciliation checks.
checks = con.execute("SELECT check_no, check_name, checked, failures FROM v_checks ORDER BY check_no").fetchall()
print(f"\n{'#':<3}{'Check':<58}{'Checked':>8}{'Failed':>8}  Result")
for no, name, checked, failures in checks:
    print(f"{no:<3}{name:<58}{checked:>8}{failures:>8}  {'PASS' if failures == 0 else 'FAIL'}")
if any(failures for *_, failures in checks):
    con.close()
    sys.exit("\nReconciliation FAILED - no JSON exported. Fix the data or the SQL first.")
print("All checks passed.\n")


# 5. Export. One JSON file per view; one record per line so git diffs stay readable.
def rows(sql):
    cur = con.execute(sql)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def plain(value):
    """DECIMAL and DOUBLE -> number with 2 decimals, dates -> 'YYYY-MM-DD'."""
    if isinstance(value, (Decimal, float)):
        return round(float(value), 2)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def write_json(name, data):
    path = EXPORT / f"{name}.json"
    if isinstance(data, list):
        lines = (json.dumps({k: plain(v) for k, v in r.items()}, ensure_ascii=False) for r in data)
        path.write_text("[\n" + ",\n".join(lines) + "\n]\n", encoding="utf-8")
    else:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {path} ({len(data) if isinstance(data, list) else 1} records)")


EXPORTS = {
    "kpis": "SELECT * FROM v_kpis ORDER BY period, basis",
    "bridge": "SELECT * FROM v_ebitda_bridge ORDER BY period, basis, step_no",
    "group_month": "SELECT * FROM v_group_month ORDER BY period, basis, sort_order",
    "material_variances": "SELECT * FROM v_material_variances ORDER BY period, rank_in_month",
    "account_month": "SELECT * FROM v_account_month ORDER BY period, account_no, cost_centre",
    "flexed_materials": "SELECT * FROM v_flexed_budget ORDER BY period, account_no",
    "account_trend": "SELECT * FROM v_account_trend ORDER BY end_period, account_no, cost_centre, month_no",
    # Only lines behind a material variance (total or price), to keep the file small.
    "transactions": """SELECT * FROM v_transactions
                       WHERE cell_id IN (SELECT cell_id FROM v_material_variances)
                       ORDER BY cell_id, posting_date, line_id""",
    # AI draft and controller's final comment side by side.
    "comments": "SELECT * FROM v_comments ORDER BY period, rank_in_month",
    # The controller's summary sentence per month; empty rows are left out.
    "month_summaries": """SELECT period, trim(summary) AS summary
                          FROM read_csv('data/ai/month_summaries.csv', header = true,
                                        columns = {'period': 'VARCHAR', 'summary': 'VARCHAR'})
                          WHERE trim(coalesce(summary, '')) <> '' ORDER BY period""",
}

EXPORT.mkdir(parents=True, exist_ok=True)
params = rows("SELECT * FROM params")[0]
write_json("meta", {
    "company_name": params["company_name"],
    "notice": "All data is synthetic. The company and all customers and suppliers are fictional.",
    "periods": [r["period"] for r in rows("SELECT period FROM periods ORDER BY period")],
    "fiscal_years": [r["fiscal_year"] for r in rows("SELECT DISTINCT fiscal_year FROM periods ORDER BY 1")],
    "latest_period": rows("SELECT MAX(period) AS p FROM periods")[0]["p"],
    "materiality": {"min_pct": params["materiality_pct"] * 100, "min_amount_dkk": plain(params["materiality_min_dkk"])},
    "sign_convention": "Amounts ending in _dkk are profit view (revenue and costs positive; "
                       "variance positive = favourable). Columns ending in _ledger_dkk are as booked "
                       "(debit +, credit -). Percentages are in per cent.",
    "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
})
for name, sql in EXPORTS.items():
    write_json(name, rows(sql))
con.close()
