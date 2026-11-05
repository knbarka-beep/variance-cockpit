"""Write data/check/spot_check.xlsx: one row per case in the pre-registered sample
(data/check/spot_check_sample.csv), for Knut to check Claude's suggested review status.

Each row shows the variance, the AI draft and labels, the five largest ledger lines, each
counterparty's change against its own 3-month average (the same table the AI saw), the three
previous months, and Claude's suggestion. The three blue columns (Agree, Knut status, Note) are
Knut's. No formulas. Never reads data/truth/ (draft_comments blocks it). Refuses to overwrite a
sheet in which any blue column has been filled in.

Run:  .venv/Scripts/python scripts/spot_check_export.py
"""
import csv

import duckdb
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation

from draft_comments import ROOT, build_input, rows
from review_suggestions import S

SAMPLE = ROOT / "data" / "check" / "spot_check_sample.csv"
SHEET = ROOT / "data" / "check" / "spot_check.xlsx"
KNUT = ["Agree", "Knut status", "Note"]
HEAD = ["variance_id", "Period", "Account", "Budget (flexed for price rows)", "Actual", "Variance (+ = favourable)",
        "AI draft (Gemini, v3a)", "AI cause", "AI persistence", "Largest ledger lines (max 5)",
        "Counterparty vs own 3-month average", "Previous 3 months (variance, + = favourable)",
        "Claude: suggested status", "Claude: suggested final comment", "Claude: why", *KNUT]
WIDTH = [27, 9, 22, 13, 13, 13, 55, 10, 11, 58, 48, 26, 12, 55, 45, 9, 12, 35]
WRAP = {7, 10, 11, 12, 14, 15, 18}  # 1-based column numbers with long text

INSTRUCTIONS = (
    "STIKKPRØVE AV CLAUDES GJENNOMGANG – 18 avvik, ca. 2 minutter per rad. Alle data er syntetiske.\n"
    "Gemini skrev utkastet (kolonne G). Claude foreslo status og eventuell ny tekst (M–O). Du sjekker om Claude har rett.\n"
    "Sjekk: 1) Nevner utkastet riktig driver ut fra hovedbokslinjene (J) og motpartstabellen (K)? "
    "2) Er Claudes status riktig etter reglene under? Bruk bare måneden og tidligere måneder (L), aldri senere.\n"
    "Regler: AVVIST (rejected) = utkastet påstår noe galt: feil fortegn, «ingen kunde/leverandør skiller seg ut» når én motpart "
    "forklarer avviket, feil måned eller tall. REDIGERT (edited) = riktig, men mangler driveren eller viktig kontekst. "
    "GODKJENT (approved) = riktig slik det står.\n"
    "Varighet: «engangs» passer når én transaksjon er større enn hele avviket; løpende kostnader første måned over/under = "
    "«for tidlig å si»; «vedvarende» bare når flere måneder på rad ligger på samme side av budsjett.\n"
    "Fyll inn de BLÅ kolonnene: Agree = Yes/No. Bare ved No: Knut status (approved/edited/rejected) og en kort Note. "
    "Lagre og lukk Excel når du er ferdig."
)


def eu(x):
    """1234567.8 -> '1.234.568' (European thousands separator, no decimals)."""
    return f"{x:,.0f}".replace(",", ".")


def knut_has_started():
    if not SHEET.exists():
        return False
    ws = load_workbook(SHEET, read_only=True).active
    all_rows = list(ws.iter_rows(values_only=True))
    h = next(i for i, r in enumerate(all_rows) if r and r[0] == "variance_id")
    cols = [all_rows[h].index(c) for c in KNUT]
    return any(r[c] not in (None, "") for r in all_rows[h + 1:] for c in cols)


def case_row(con, vid):
    v = rows(con, "SELECT * FROM v_material_variances WHERE variance_id = ?", [vid])[0]
    d = rows(con, "SELECT ai_comment, ai_cause_category, ai_persistence FROM v_comments WHERE variance_id = ?", [vid])[0]
    inp = build_input(con, v)  # only this month and earlier
    sign = 1 if v["pl_group"] == "Revenue" else -1  # show revenue and costs as positive amounts
    lines = "\n".join(f"{x['counterparty'] or '(none)'} | {eu(-sign * x['amount_dkk'])} | {x['description']}"
                      for x in inp["ledger_lines"][:5])
    table = inp.get("revenue_by_customer") or inp.get("cost_by_supplier") or []
    name = "customer" if "revenue_by_customer" in inp else "supplier"
    amount = "revenue_dkk" if name == "customer" else "cost_dkk"
    cps = "\n".join(f"{t[name] or '(none)'}: {eu(t[amount])} vs {eu(t['avg_prev_3_months_dkk'] or 0)}"
                    for t in table[:3]) or "(not used for raw materials: see the flexed budget)"
    prev = "\n".join(f"{p['period']}: {'+' if p['variance_dkk'] >= 0 else '−'}{eu(abs(p['variance_dkk']))}"
                     for p in inp["previous_months"])
    budget = v["flexed_budget_dkk"] if v["variance_type"] == "price" else v["budget_dkk"]
    st, final, why = S[vid]
    return [vid, v["period"], f"{v['account_no']} {v['account_name']}, {v['cost_centre']}"
            + (" (price row)" if v["variance_type"] == "price" else ""),
            budget, v["actual_dkk"], v["variance_profit_dkk"], d["ai_comment"], d["ai_cause_category"],
            d["ai_persistence"], lines, cps, prev, st, final or "(none: approved as written)", why, "", "", ""]


def main():
    assert not knut_has_started(), f"{SHEET} already has Knut's input; not overwriting"
    sample = sorted(r["variance_id"] for r in csv.DictReader(SAMPLE.open(encoding="utf-8")))
    assert len(sample) == 18, len(sample)
    con = duckdb.connect(str(ROOT / "data" / "variance.duckdb"), read_only=True)

    wb = Workbook()
    ws = wb.active
    ws.title = "Spot check"
    n = len(HEAD)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=n)
    box = ws.cell(1, 1, INSTRUCTIONS)
    box.alignment = Alignment(wrap_text=True, vertical="top")
    box.fill = PatternFill("solid", fgColor="F2F2F2")
    box.font = Font(size=11)
    ws.row_dimensions[1].height = 135
    ws.append(HEAD)
    for vid in sample:
        ws.append(case_row(con, vid))
    con.close()

    last = ws.max_row
    agree = DataValidation(type="list", formula1='"Yes,No"', allow_blank=True)
    status = DataValidation(type="list", formula1='"approved,edited,rejected"', allow_blank=True)
    ws.add_data_validation(agree)
    ws.add_data_validation(status)
    agree.add(f"P3:P{last}")
    status.add(f"Q3:Q{last}")

    blue, claude = PatternFill("solid", fgColor="BDD7EE"), PatternFill("solid", fgColor="FFF2CC")
    thin = Side(style="thin", color="BFBFBF")
    for i, w in enumerate(WIDTH, 1):
        ws.column_dimensions[ws.cell(2, i).column_letter].width = w
    for row in ws.iter_rows(min_row=2, max_row=last):
        for c in row:
            c.alignment = Alignment(vertical="top", wrap_text=c.row == 2 or c.column in WRAP)
            c.border = Border(top=thin, bottom=thin, left=thin, right=thin)
            if c.column >= 16:
                c.fill = blue
            elif c.column >= 13:
                c.fill = claude
            if c.row == 2:
                c.font = Font(bold=True)
            elif 4 <= c.column <= 6:
                c.number_format = "#,##0"
    ws.freeze_panes = "B3"
    wb.save(SHEET)
    print(f"wrote {SHEET.relative_to(ROOT)}: {last - 2} rows")


if __name__ == "__main__":
    main()
