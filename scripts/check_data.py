"""Check the generated data and build an Excel file for manual verification.

Run after generate_data.py:  .venv/Scripts/python scripts/check_data.py

Prints: revenue and EBITDA per fiscal year, material variances per month,
whether each planted event shows up, and a reconciliation of ledger lines
against the monthly totals in data/check/variance_check.xlsx.

Variance = actual - budget in ledger sign (debit +, credit -), so a positive
variance always lowers profit (unfavourable), for revenue and costs alike.
"""
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
cfg = yaml.safe_load((ROOT / "config" / "settings.yaml").read_text(encoding="utf-8"))
raw = ROOT / "data" / "raw"
tables = {n: pd.read_csv(raw / f"{n}.csv") for n in
          ["accounts", "cost_centres", "counterparties", "budget", "gl_transactions"]}
gl, budget, accounts = tables["gl_transactions"], tables["budget"], tables["accounts"]
truth = pd.read_csv(ROOT / "data" / "truth" / "planted_events.csv", dtype=str)
KEYS = ["period", "account_no", "cost_centre"]
fy_start = cfg["period"]["fiscal_year_start_month"]
mat = cfg["materiality"]

# ---------------------------------------------------------------- monthly actual vs budget
actual = gl.groupby(KEYS, as_index=False)["amount_dkk"].sum().rename(columns={"amount_dkk": "actual_dkk"})
monthly = (budget.rename(columns={"amount_dkk": "budget_dkk"})
           .merge(actual, on=KEYS, how="outer").fillna({"actual_dkk": 0.0, "budget_dkk": 0.0})
           .merge(accounts[["account_no", "account_name", "pl_group"]], on="account_no"))
month = pd.PeriodIndex(monthly["period"], freq="M")
monthly.insert(0, "fiscal_year", ["FY%d" % (p.year + (p.month >= fy_start)) for p in month])


def add_variance(df, base, prefix):
    var = df["actual_dkk"] - df[base]
    df[f"{prefix}variance_dkk"] = var.round(2)
    df[f"{prefix}variance_pct"] = (var / df[base].abs()).where(df[base] != 0).round(4)
    df[f"{prefix}material"] = (var.abs() >= mat["min_amount_dkk"]) & (var.abs() >= mat["min_pct"] * df[base].abs())


add_variance(monthly, "budget_dkk", "")

# Flexed budget: materials budget scaled by actual/budget sales volume (revenue ratio).
# It separates price effects from volume effects on volume-driven costs.
is_rev = monthly["pl_group"] == "Revenue"
rev = monthly[is_rev].groupby("period")[["actual_dkk", "budget_dkk"]].sum()
volume_ratio = monthly["period"].map(rev["actual_dkk"] / rev["budget_dkk"])
monthly["flexed_budget_dkk"] = monthly["budget_dkk"].where(
    monthly["pl_group"] != "Cost of materials", (monthly["budget_dkk"] * volume_ratio).round(2))
add_variance(monthly, "flexed_budget_dkk", "flexed_")

by_group = monthly.groupby(["fiscal_year", "period", "pl_group"], as_index=False)[["actual_dkk", "budget_dkk"]].sum()
by_group["variance_dkk"] = by_group["actual_dkk"] - by_group["budget_dkk"]

# ---------------------------------------------------------------- 1. revenue and EBITDA per year
fmt = lambda x: f"{x:>15,.0f}"
print(f"\n{cfg['company']['name']} - ALL DATA SYNTHETIC\n")
print("1. Revenue and EBITDA per fiscal year (DKK, shown as positive = profit)")
print(f"{'':22}{'Actual':>15}{'Budget':>15}{'Variance':>15}")
for fy, g in monthly.groupby("fiscal_year"):
    for label, rows in [("Revenue", g[g["pl_group"] == "Revenue"]), ("EBITDA", g)]:
        a, b = -rows["actual_dkk"].sum(), -rows["budget_dkk"].sum()
        print(f"  {fy} {label:<15}{fmt(a)}{fmt(b)}{fmt(a - b)}")

# ---------------------------------------------------------------- 2. material variances per month
print(f"\n2. Material variances per month (>= {mat['min_pct']:.0%} AND >= DKK {mat['min_amount_dkk']:,})")
for period, g in monthly.groupby("period"):
    hits = g[g["material"]]
    names = ", ".join(f"{r.account_no} {r.cost_centre} ({r.variance_dkk:+,.0f})" for r in hits.itertuples())
    print(f"  {period}: {len(hits):>2}  {names}")

# ---------------------------------------------------------------- 3. planted events
print("\n3. Planted events - material in the expected months, in the expected direction?")
lookup = monthly.set_index(["period", "account_no", "cost_centre"])
for e in truth.itertuples():
    periods = e.periods.split(";")
    dirs = e.expected_direction.split(";")
    dirs = dirs * len(periods) if len(dirs) == 1 else dirs
    prefix = "flexed_" if e.check_basis == "flexed budget" else ""
    results = []
    lines = []
    for period, direction in zip(periods, dirs):
        for acc in e.accounts.split(";"):
            r = lookup.loc[(period, int(acc), e.cost_centre)]
            var, material = r[f"{prefix}variance_dkk"], r[f"{prefix}material"]
            ok = bool(material) and (var > 0) == (direction == "unfavourable")
            results.append(ok)
            extra = f" | vs plain budget {r['variance_dkk']:+,.0f}, material: {'yes' if r['material'] else 'no'}" if prefix else ""
            lines.append(f"     {period} {acc} {e.cost_centre:<14} {var:>+12,.0f} ({r[f'{prefix}variance_pct']:+.1%})"
                         f"  expected {direction:<12} -> {'yes' if ok else 'NO'}{extra}")
    print(f"  Event {e.event_id} (checked against {e.check_basis}): {'YES' if all(results) else 'NO'}")
    print("\n".join(lines))

# ---------------------------------------------------------------- Excel file for manual checks
xlsx = ROOT / "data" / "check" / "variance_check.xlsx"
xlsx.parent.mkdir(parents=True, exist_ok=True)
with pd.ExcelWriter(xlsx) as w:
    for name, df in tables.items():
        df.to_excel(w, sheet_name=name, index=False)
    monthly.to_excel(w, sheet_name="monthly_by_account", index=False)
    by_group.to_excel(w, sheet_name="monthly_by_group", index=False)

# ---------------------------------------------------------------- 4. reconciliation
# Read the Excel file back and compare it with a fresh sum of the raw ledger lines.
sheet = pd.read_excel(xlsx, sheet_name="monthly_by_account", dtype={"period": str})
fresh = gl.groupby(KEYS)["amount_dkk"].sum()
diff_account = (sheet.set_index(KEYS)["actual_dkk"] - fresh).abs().max()
sheet_group = pd.read_excel(xlsx, sheet_name="monthly_by_group", dtype={"period": str})
fresh_group = gl.merge(accounts, on="account_no").groupby(["period", "pl_group"])["amount_dkk"].sum()
diff_group = (sheet_group.set_index(["period", "pl_group"])["actual_dkk"] - fresh_group).abs().max()
ok = len(sheet) == len(fresh) and diff_account < 0.01 and diff_group < 0.01
print("\n4. Reconciliation: ledger lines vs monthly totals in the Excel file")
print(f"  {len(gl)} ledger lines, {len(fresh)} account/cost centre/month totals")
print(f"  Largest difference per account/cost centre/month: DKK {diff_account:.2f}")
print(f"  Largest difference per P&L group/month:          DKK {diff_group:.2f}")
print(f"  Result: {'OK - totals match' if ok else 'MISMATCH'}")
print(f"\nExcel check file written to {xlsx.relative_to(ROOT)}")
