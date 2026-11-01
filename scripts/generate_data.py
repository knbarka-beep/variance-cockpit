"""Generate the synthetic data set for Variance Cockpit.

Reads every assumption from config/settings.yaml and writes:
  data/raw/    accounts, cost_centres, counterparties, budget, gl_transactions
  data/truth/  planted_events (the answer key - never input to AI or dashboard)

All data is synthetic and the company is fictional.
Run from the project folder:  .venv/Scripts/python scripts/generate_data.py

Sign convention (as in a real ledger): debit = positive, credit = negative.
Revenue is therefore negative and costs positive.
"""
from collections import defaultdict
from itertools import count
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
cfg = yaml.safe_load((ROOT / "config" / "settings.yaml").read_text(encoding="utf-8"))
rng = np.random.default_rng(cfg["random_seed"])  # fixed seed -> identical data every run

months = pd.period_range(cfg["period"]["first_month"], cfg["period"]["last_month"], freq="M")
fy_start = cfg["period"]["fiscal_year_start_month"]
season = {int(k): v for k, v in cfg["seasonality"].items()}
season_mean = sum(season.values()) / 12
price = cfg["selling_price_per_unit_dkk"]
sd = cfg["noise"]["monthly_sd"]
ev = cfg["events"]
P = lambda text: pd.Period(text, freq="M")  # "2026-06" -> a month


def fiscal_year(m):
    return f"FY{m.year + 1 if m.month >= fy_start else m.year}"


def annual_revenue(m):
    """Budgeted revenue for the fiscal year the month belongs to."""
    return cfg["budget_revenue_per_fiscal_year"][fiscal_year(m)]


def monthly_revenue(m):
    return annual_revenue(m) / 12 * season[m.month] / season_mean


def month_name(m):
    return m.strftime("%B %Y")  # "September 2026"


# ---------------------------------------------------------------- budget
# One amount per account, cost centre and month. Revenue and materials follow
# the seasonal sales volume; staff costs and other expenses are flat each month.
budget_rows = []
for m in months:
    revenue = monthly_revenue(m)
    volume = revenue / price  # units sold
    for a in cfg["accounts"]:
        group = a["pl_group"]
        if group == "Revenue":
            share = sum(c["share"] for c in cfg["customers"] if c["market"] == a["market"])
            amount = -revenue * share  # credit = negative
        elif group == "Cost of materials":
            unit_cost = price * cfg["cost_structure"][group] * a["group_share"]
            amount = volume * unit_cost
        else:
            amount = annual_revenue(m) * cfg["cost_structure"][group] * a["group_share"] / 12
        for cc, cc_share in a["cost_centres"].items():
            budget_rows.append({"period": str(m), "account_no": a["account_no"], "cost_centre": cc,
                                "amount_dkk": round(amount * cc_share, 2)})
budget = pd.DataFrame(budget_rows)
bud = budget.set_index(["period", "account_no", "cost_centre"])["amount_dkk"]

# ---------------------------------------------------------------- helpers for actuals
lines = []  # one dict per ledger line
planted = defaultdict(lambda: defaultdict(float))  # event_id -> period -> effect in DKK (ledger sign)


def post(m, account_no, cc, amount, text, counterparty="", day=None, voucher=None):
    """Add one general ledger line."""
    day = day or int(rng.integers(1, m.days_in_month + 1))
    lines.append({"voucher_key": voucher or f"auto{len(lines)}", "posting_date": f"{m}-{day:02d}",
                  "period": str(m), "account_no": account_no, "cost_centre": cc,
                  "counterparty": counterparty, "description": text, "amount_dkk": round(float(amount), 2)})


def split(total, n):
    """Split an amount into n random pieces that add up exactly to the total."""
    parts = np.round(total * rng.dirichlet(np.full(n, 4.0)), 2)
    parts[-1] = round(total - parts[:-1].sum(), 2)
    return parts


def invoice_no():
    return int(rng.integers(10000, 100000))


def noise(s=sd):
    """Random factor around 1 (mean exactly 1)."""
    return 1 + rng.normal(0, s)


timing = {}


def timing_noise(account_no, cc, m, s):
    """Monthly factor for costs: monthly swings that cancel out over the fiscal year,
    plus one small drift for the whole year (e.g. +2 % means the year lands 2 % over budget)."""
    key = (account_no, cc, fiscal_year(m))
    if key not in timing:
        z = np.clip(rng.normal(0, s, 12), -0.75, 0.75)  # symmetric cap, so still mean zero
        d = cfg["noise"]["annual_drift_sd"]
        drift = np.clip(rng.normal(0, d), -2.5 * d, 2.5 * d)  # symmetric cap: at most +/-5 % at sd 2 %
        timing[key] = 1 + z - z.mean() + drift  # remove the year's average swing, add the drift
        assert timing[key].min() > 0, f"noise_sd too high for account {account_no}: a month would turn negative"
    return timing[key][(m.month - fy_start) % 12]


suppliers = defaultdict(list)
for s in cfg["suppliers"]:
    suppliers[s["account_no"]].append(s)
rev_account = {a["market"]: a["account_no"] for a in cfg["accounts"] if a["pl_group"] == "Revenue"}

# ---------------------------------------------------------------- revenue (per customer)
# Revenue = budget share per customer x small noise. The ratio actual/budget revenue
# is the month's volume factor, which drives raw materials and packaging below.
volume_factor = {}
sales_invoice = count(10001)
e4 = ev["key_customer_volume_cut"]
for m in months:
    budget_total = monthly_revenue(m)
    actual_total = 0.0
    for c in cfg["customers"]:
        actual = budget_total * c["share"] * noise()
        if c["name"] == e4["customer"] and m >= P(e4["from_period"]):  # event 4
            planted[4][str(m)] += actual * e4["cut"]  # less revenue = positive in ledger sign
            actual *= 1 - e4["cut"]
        for amount in split(actual, int(rng.integers(1, 4))):
            post(m, rev_account[c["market"]], "Sales", -amount,
                 f"Invoice {next(sales_invoice)}, {rng.choice(cfg['products'])}", c["name"])
        actual_total += actual
    volume_factor[str(m)] = actual_total / budget_total

# ---------------------------------------------------------------- costs (normal months)
e1, e5, e3 = ev["raw_material_price_increase"], ev["sick_leave_production"], ev["energy_misposting"]
for m in months:
    for a in cfg["accounts"]:
        no = a["account_no"]
        if a["pl_group"] == "Revenue" or no == e3["account_no"]:  # energy is handled separately
            continue
        for cc in a["cost_centres"]:
            target = bud[(str(m), no, cc)]
            if a["pl_group"] == "Cost of materials":
                target *= volume_factor[str(m)]  # materials move with sales volume
            if not a.get("fixed"):
                target *= timing_noise(no, cc, m, a.get("noise_sd", sd))
            if no == e1["account_no"] and m >= P(e1["from_period"]):  # event 1
                planted[1][str(m)] += target * e1["increase"]
                target *= 1 + e1["increase"]
            if no == e5["overtime_account_no"] and str(m) in e5["periods"]:  # event 5, overtime
                planted[5][str(m)] += e5["extra_overtime_dkk"]
                target += e5["extra_overtime_dkk"]

            for amount in split(target, a["lines_per_month"]):
                if "payroll_text" in a:  # payroll: no counterparty, booked on the last day
                    post(m, no, cc, amount, a["payroll_text"].format(month=month_name(m), cc=cc.lower()),
                         day=m.days_in_month)
                elif "generic_texts" in a and rng.random() < 0.3:  # card payments etc.
                    post(m, no, cc, amount, str(rng.choice(a["generic_texts"])))
                else:
                    s = suppliers[no][rng.integers(len(suppliers[no]))]
                    week = int(m.start_time.isocalendar().week) + int(rng.integers(0, 4))
                    item = str(rng.choice(s["items"])).format(month=month_name(m), week=week)
                    post(m, no, cc, amount, f"Invoice {invoice_no()}, {item}", s["name"])

# ---------------------------------------------------------------- energy (event 3)
# Energy is invoiced quarterly and normally spread as one third per month.
energy_supplier = suppliers[e3["account_no"]][0]["name"]
energy_key = lambda m: (str(m), e3["account_no"], e3["cost_centre"])
for m in months:
    if m.month % 3 == 1:  # first month of a quarter: new invoice
        q_amount = round(sum(bud[energy_key(m + i)] for i in range(3)) * noise(), 2)
        q_invoice, q_label = invoice_no(), f"Q{(m.month - 1) // 3 + 1} {m.year}"
    share = round(q_amount / 3, 2)
    acc, cc = e3["account_no"], e3["cost_centre"]
    if m == P(e3["period"]):  # whole quarter booked in one month
        post(m, acc, cc, q_amount, f"Invoice {q_invoice}, electricity and gas {q_label}", energy_supplier, day=12)
        planted[3][str(m)] += q_amount - share
    elif m == P(e3["period"]) + 1:  # reversal and correct postings, in one voucher
        v = "energy-correction"
        post(m, acc, cc, -q_amount, f"Reversal of invoice {q_invoice}, electricity and gas {q_label}",
             energy_supplier, day=8, voucher=v)
        post(m, acc, cc, share, f"Invoice {q_invoice}, electricity and gas {month_name(m - 1)}",
             energy_supplier, day=8, voucher=v)
        post(m, acc, cc, share, f"Invoice {q_invoice}, electricity and gas {month_name(m)}",
             energy_supplier, day=8, voucher=v)
        planted[3][str(m)] += -q_amount + share
    else:
        post(m, acc, cc, share, f"Invoice {q_invoice}, electricity and gas {month_name(m)}", energy_supplier, day=12)

# ---------------------------------------------------------------- one-off events
e2 = ev["machine_repair"]  # event 2: one large supplier invoice
post(P(e2["period"]), e2["account_no"], e2["cost_centre"], e2["amount_dkk"], e2["text"], e2["supplier"], day=18)
planted[2][e2["period"]] += e2["amount_dkk"]

for period in e5["periods"]:  # event 5: weekly agency invoices for temporary staff
    m = P(period)
    first_week = int(m.start_time.isocalendar().week)
    agencies = suppliers[e5["temporary_staff_account_no"]]
    for i, amount in enumerate(split(e5["extra_temporary_staff_dkk"], 4)):
        post(m, e5["temporary_staff_account_no"], e5["cost_centre"], amount,
             f"Invoice {invoice_no()}, temporary staff week {first_week + i}, production",
             agencies[i % len(agencies)]["name"], day=7 * i + 5)
    planted[5][period] += e5["extra_temporary_staff_dkk"]

e6 = ev["unexplained_admin_overspend"]  # event 6: many small, generic transactions
acc6 = next(a for a in cfg["accounts"] if a["account_no"] == e6["account_no"])
for amount in split(e6["extra_dkk"], e6["transactions"]):  # same style as normal card payments
    post(P(e6["period"]), e6["account_no"], e6["cost_centre"], amount, str(rng.choice(acc6["generic_texts"])))
planted[6][e6["period"]] += e6["extra_dkk"]

# ---------------------------------------------------------------- write raw tables
raw = ROOT / "data" / "raw"
truth_dir = ROOT / "data" / "truth"
raw.mkdir(parents=True, exist_ok=True)
truth_dir.mkdir(parents=True, exist_ok=True)

gl = pd.DataFrame(lines).sort_values("posting_date", kind="stable")
gl["voucher_no"] = pd.factorize(gl["voucher_key"])[0] + 100001  # numbered in date order
gl["line_id"] = range(1, len(gl) + 1)
gl = gl[["line_id", "voucher_no", "posting_date", "period", "account_no", "cost_centre",
         "counterparty", "description", "amount_dkk"]]

accounts = pd.DataFrame([{"account_no": a["account_no"], "account_name": a["name"], "pl_group": a["pl_group"],
                          "allowed_cost_centres": ";".join(a["cost_centres"])} for a in cfg["accounts"]])
cost_centres = pd.DataFrame(cfg["cost_centres"])
counterparties = pd.DataFrame(
    [{"counterparty": c["name"], "type": "customer", "country": c["country"], "default_account_no": rev_account[c["market"]]}
     for c in cfg["customers"]]
    + [{"counterparty": s["name"], "type": "supplier", "country": s["country"], "default_account_no": s["account_no"]}
       for s in cfg["suppliers"]])

for name, df in [("accounts", accounts), ("cost_centres", cost_centres), ("counterparties", counterparties),
                 ("budget", budget), ("gl_transactions", gl)]:
    df.to_csv(raw / f"{name}.csv", index=False, float_format="%.2f")

# ---------------------------------------------------------------- write answer key
def truth_row(event_id, description, accounts_, cc, check_basis="budget"):
    effect = planted[event_id]
    periods = sorted(effect)
    dirs = ["unfavourable" if effect[p] > 0 else "favourable" for p in periods]
    return {"event_id": event_id, "description": description, "accounts": ";".join(map(str, accounts_)),
            "cost_centre": cc, "periods": ";".join(periods),
            "expected_direction": dirs[0] if len(set(dirs)) == 1 else ";".join(dirs),
            "approximate_size_dkk": ";".join(f"{round(effect[p], -3):+.0f}" for p in periods),
            "check_basis": check_basis}


truth = pd.DataFrame([
    truth_row(1, f"Raw material prices rise by about {e1['increase']:.0%} from {e1['from_period']} and stay higher. "
                 "From the month the key customer cuts volume (event 4), lower volume pulls raw material spend down "
                 "and hides part of the price effect, so this event is tested against the volume-adjusted (flexed) budget.",
              [e1["account_no"]], e1["cost_centre"], check_basis="flexed budget"),
    truth_row(2, f"One-off emergency repair of a hydraulic press: one supplier invoice of DKK {e2['amount_dkk']} "
                 f"from {e2['supplier']}.", [e2["account_no"]], e2["cost_centre"]),
    truth_row(3, "Quarterly energy invoice booked in full in one month instead of one third per month, "
                 "then reversed and rebooked correctly the following month. Overspend first, underspend second.",
              [e3["account_no"]], e3["cost_centre"]),
    truth_row(4, f"Key customer {e4['customer']} cuts volume by about {e4['cut']:.0%}. Domestic revenue falls. "
                 "Raw materials and packaging fall with volume, but that effect alone is below the threshold.",
              [rev_account["domestic"]], "Sales"),
    truth_row(5, "Sick leave in Production covered by extra overtime and temporary staff agency invoices. "
                 "Wages are unchanged because sick pay is still paid. Size is the total of both accounts.",
              [e5["overtime_account_no"], e5["temporary_staff_account_no"]], e5["cost_centre"]),
    truth_row(6, "Many small purchases with generic descriptions push other external costs above budget. "
                 "There is no single cause in the data; the correct conclusion is that the cause is unclear.",
              [e6["account_no"]], e6["cost_centre"]),
])
truth.to_csv(truth_dir / "planted_events.csv", index=False)

print(f"Wrote {len(gl)} ledger lines, {len(budget)} budget rows and {len(truth)} planted events.")
