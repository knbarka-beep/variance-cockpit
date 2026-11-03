"""Write data/check/review.xlsx with Claude's SUGGESTED review columns for all 71 v3a drafts.

The suggestions are written by hand below (S) from the ledger, the budget and months up to the
row's month only. Never data/truth/. The last three columns (status, final_comment, reviewer_note)
are left empty for the controller and keep the names review_import.py reads. The script refuses to
overwrite a workbook in which the controller has already filled in any of those columns.

Rules used for the suggestions:
  Status   rejected = the draft claims something wrong (wrong sign, "no customer stands out" when one
           counterparty explains it, a wrong month or figure); edited = right, but misses the driver
           or important context; approved = right as written.
  Persistence
           a) one identifiable transaction (one invoice, a correction or reversal) larger than the
              whole variance: "one-off" is fine, also in the first month;
           b) running lines (payroll, overtime, temporary staff, regular suppliers, many similar
              lines) in the first month over or under budget: "too early to tell";
           c) several months in a row on the same side of budget in the ledger: "persistent" is fine.
  Text     British English, at most 60 words, European number format, no Cause/Persistence labels.

Run:  .venv/Scripts/python scripts/review_suggestions.py   then   scripts/check_suggestions.py
"""
import csv
import json
import re
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = ROOT / "data" / "check" / "review.xlsx"

A, E, X = "approved", "edited", "rejected"
TOO_EARLY_UP = "so it is too early to tell whether the higher level lasts."
TOO_EARLY_DOWN = "so it is too early to tell whether the lower level lasts."

# variance_id: (SUGGESTED status, SUGGESTED final_comment, why suggested)
S = {
    # ---------------------------------------------------------------- 2026-09
    "2026-09_1010_Sales": (X,
        "Domestic product revenue was DKK 0,51m (8,6 %) below budget, the third month in a row (July 8,0 %, "
        "August 9,3 %). Nordvik Maskinfabrik A/S invoiced DKK 1,62m against DKK 2,15m in June, a drop of "
        "DKK 0,53m that explains the whole shortfall; other customers are at June levels. The drop has lasted since July.",
        "AI wrong: says no customer stands out, but Nordvik Maskinfabrik A/S explains the whole shortfall against June; "
        "it also misses that this is the third month in a row."),
    "2026-09_2010_Production_price": (E,
        "Measured against the flexed budget (volume 95,3 % of budget), raw materials cost DKK 0,37m (9,0 %) more, "
        "so the cost per unit is higher than budgeted. The ledger lines show no unit prices or quantities, so the "
        "cause is not visible. June, July and August were also over the flexed budget.",
        "Added context: 'persistent' is right, but the draft does not say the variance is against the flexed budget "
        "or that it means a higher cost per unit."),
    "2026-09_4010_Production": (A, "",
        "Correct: one emergency repair invoice (DKK 0,35m) is larger than the whole variance, so 'one-off' fits."),
    "2026-09_3030_Production": (E,
        "Temporary staff in production cost DKK 0,29m against a budget of DKK 0,09m, DKK 0,20m over. August was "
        "also over budget at the same level. Vikarhuset Odense ApS (DKK 0,18m) and ProBemanding Fyn A/S "
        "(DKK 0,11m) supplied the staff. The ledger does not show why extra staff were needed.",
        "Added context: compares with budget and names both agencies; the draft uses the American spelling 'unfavorable'."),
    "2026-09_3020_Production": (E,
        "Overtime in production was DKK 0,22m against a budget of DKK 0,12m, DKK 0,10m over. August was also "
        "over budget at the same level. The cost is one payroll line, so the ledger does not show which teams or "
        "why. Temporary staff rose in the same two months.",
        "Added context: the draft misses that August was at the same level, and it is one payroll line, "
        "not lines without a counterparty to chase."),
    "2026-09_4090_Administration": (A, "",
        "Correct: lines without a counterparty (card payments, expense claims) rose to DKK 0,14m and no supplier explains the variance."),
    # ---------------------------------------------------------------- 2026-08
    "2026-08_4020_Production": (E,
        "Energy was DKK 0,58m below budget because of a posting correction. In July, invoice 32025 from Fyns "
        "Energiforsyning A/S was booked for the whole of Q3 (DKK 0,87m). In August it was reversed and rebooked "
        "for July and August only (DKK 0,29m each). Taken together, the two months match the budget; this is not a saving.",
        "Added context: names the reversal but does not link it to the July overbooking, so a reader may see a real saving."),
    "2026-08_1010_Sales": (E,
        "Domestic product revenue was DKK 0,53m (9,3 %) below budget. July was also below budget (8,0 %). "
        "Nordvik Maskinfabrik A/S invoiced DKK 1,54m against DKK 2,15m in June and explains most of the gap. "
        "The customer has bought less since July, so this should not be treated as timing.",
        "Added context: Nordvik is the right driver, but 'timing' is not supported; revenue was also below budget in July."),
    "2026-08_2010_Production_price": (E,
        "Measured against the flexed budget (volume 95,3 % of budget), raw materials cost DKK 0,24m (6,0 %) more, "
        "so the cost per unit is higher than budgeted. The ledger lines show no unit prices or quantities, so the "
        "cause is not visible. June and July were also over the flexed budget.",
        "Added context: 'persistent' is right, but the draft does not say the variance is against the flexed budget "
        "or that it means a higher cost per unit."),
    "2026-08_3030_Production": (E,
        "Temporary staff in production cost DKK 0,29m against a budget of DKK 0,09m, DKK 0,20m over. July was "
        "close to budget. ProBemanding Fyn A/S (DKK 0,17m) and Vikarhuset Odense ApS (DKK 0,12m) both invoiced "
        "more. The ledger does not show why, " + TOO_EARLY_UP,
        "Added context: weekly agency invoices are running costs, so 'one-off' is too early in the first month over; "
        "Vikarhuset also rose."),
    "2026-08_3020_Production": (E,
        "Overtime in production was DKK 0,22m against a budget of DKK 0,12m, DKK 0,10m over. The cost is one payroll line, so the ledger does not show which teams or why. Temporary staff "
        "also rose in August. It is the first month over budget, " + TOO_EARLY_UP,
        "Added context: overtime is a running cost; the draft calls it both one-off and unknown in the first month over."),
    "2026-08_4010_Production": (A, "",
        "Correct: the lower spend is spread over several suppliers, with no single cause, and no persistence claim is made."),
    # ---------------------------------------------------------------- 2026-07
    "2026-07_4020_Production": (A, "",
        "Correct: one invoice for the whole of Q3 2026, about three months of budget, was booked in July."),
    "2026-07_1010_Sales": (X,
        "Domestic product revenue was DKK 0,34m (8,0 %) below budget. Nordvik Maskinfabrik A/S invoiced DKK 1,18m "
        "against a three-month average of DKK 2,14m. Other customers fell roughly in line with the lower July "
        "budget, so Nordvik explains most of the shortfall. June was on budget, so it is too early to tell whether "
        "the lower level lasts.",
        "AI wrong: says no single cause, but against the seasonal July budget only Nordvik Maskinfabrik A/S fell clearly more than the rest."),
    "2026-07_2010_Production_price": (E,
        "Measured against the flexed budget (volume 95,5 % of budget), raw materials cost DKK 0,23m (7,7 %) more, "
        "so the cost per unit is higher than budgeted. The ledger lines show no unit prices or quantities, so the "
        "cause is not visible. June was also over the flexed budget (DKK 0,37m).",
        "Added context: the draft does not say the variance is against the flexed budget, or that June was also over it."),
    "2026-07_4050_Sales": (A, "",
        "Correct: Messepartner Danmark ApS invoiced nothing, and the persistence is left open."),
    "2026-07_4090_Administration": (E,
        "Other external costs were DKK 0,05m (56,9 %) over budget. CleanTeam Fyn ApS invoiced DKK 0,06m for "
        "cleaning services, against small amounts in the previous three months, and Revisionsfirmaet Bogelund & Co "
        "invoiced DKK 0,04m for audit and accounting advice. June was also over budget.",
        "Added context: no single invoice is larger than the variance, so 'one-off' is not supported, and June was also over budget."),
    # ---------------------------------------------------------------- 2026-06
    "2026-06_2010_Production": (E,
        "Raw materials were DKK 0,38m (8,8 %) over budget. Volume was 100,3 % of budget, so almost all of it, "
        "DKK 0,37m, is a price or usage effect against the flexed budget. The ledger shows no unit prices. May was close to the flexed budget, " + TOO_EARLY_UP,
        "Added context: 'raw material pricing' is not visible without unit prices; first month over on many supplier lines, so too early to tell."),
    "2026-06_2010_Production_price": (E,
        "Measured against the flexed budget (volume 100,3 % of budget), raw materials cost DKK 0,37m (8,5 %) more, "
        "so the cost per unit is higher than budgeted. The ledger shows no unit prices or quantities. May was close to the flexed budget, " + TOO_EARLY_UP,
        "Added context: the draft does not say the variance is against the flexed budget; first month over, so too early to tell."),
    "2026-06_4010_Production": (E,
        "Repairs and maintenance were DKK 0,11m (40,7 %) over budget. ElektroTeknik Tarup ApS invoiced DKK 0,20m "
        "for control panel inspections, against DKK 0,10m on average in the previous three months. May was also "
        "over budget; the ledger does not show why.",
        "Added context: driver is right, but 'timing' is not visible in the ledger, and May was also over budget."),
    "2026-06_4040_Administration": (E,
        "IT costs were DKK 0,07m (43,3 %) under budget. Odense IT-Drift ApS invoiced nothing, against DKK 0,08m "
        "on average in the previous three months. April and May were also under budget, so this is the third month "
        "in a row; the ledger does not show why.",
        "Added context: driver is right, but it is the third month under budget, not a timing swing month."),
    "2026-06_4090_Administration": (E,
        "Other external costs were DKK 0,06m (66,7 %) over budget. Kontorhuset Fyn ApS invoiced DKK 0,06m for "
        "office supplies, against DKK 0,03m on average in the previous three months, and card payments without a "
        "counterparty also rose. May was under budget, " + TOO_EARLY_UP,
        "Added context: office supplies and card payments are running costs; first month over, so too early to tell."),
    "2026-06_4050_Sales": (A, "",
        "Correct: trade fair invoices from Messepartner Danmark ApS, and the persistence is left open."),
    # ---------------------------------------------------------------- 2026-05
    "2026-05_4050_Sales": (X,
        "Marketing was DKK 0,09m (69,1 %) under budget. Messepartner Danmark ApS invoiced DKK 0,04m, against "
        "DKK 0,13m on average in the previous three months, which explains most of the gap. April was over "
        "budget, " + TOO_EARLY_DOWN,
        "AI wrong: says the changes span several suppliers, but only Messepartner Danmark ApS invoiced, and it explains almost all of the variance."),
    "2026-05_4010_Production": (E,
        "Repairs and maintenance were DKK 0,09m (33,9 %) over budget. Hydra-Service Danmark ApS invoiced DKK 0,16m "
        "for hydraulic press service visits, against DKK 0,07m on average in the previous three months. April was "
        "on budget, " + TOO_EARLY_UP,
        "Added context: driver is right, but routine service visits are running costs; first month over, so too early to tell."),
    "2026-05_4040_Administration": (E,
        "IT costs were DKK 0,09m (55,4 %) under budget. Odense IT-Drift ApS invoiced nothing, against DKK 0,12m "
        "on average in the previous three months. April was also under budget; the ledger does not show why the "
        "supplier has not invoiced.",
        "Added context: driver is right, but 'timing in invoice processing' is not in the ledger, and April was also under budget."),
    # ---------------------------------------------------------------- 2026-04
    "2026-04_4050_Sales": (A, "",
        "Correct: one trade fair invoice from Messepartner Danmark ApS (DKK 0,21m) is larger than the whole variance, so 'one-off' fits."),
    "2026-04_4040_Administration": (X,
        "IT costs were DKK 0,08m (53,2 %) under budget. Odense IT-Drift ApS invoiced DKK 0,05m against DKK 0,12m "
        "on average in the previous three months, and Nordlys Software A/S invoiced nothing against DKK 0,06m. "
        "March was over budget, " + TOO_EARLY_DOWN,
        "AI wrong: says no supplier explains half, but Odense IT-Drift alone explains over 80 %, and it writes an amount with a minus sign."),
    # ---------------------------------------------------------------- 2026-03
    "2026-03_4010_Production": (E,
        "Repairs and maintenance were DKK 0,12m (43,7 %) under budget. Fynsk Maskinreparation ApS invoiced "
        "DKK 0,02m, against DKK 0,17m on average in the previous three months, an average raised by a large "
        "invoice in January. February was on budget, " + TOO_EARLY_DOWN,
        "Added context: driver is right, but 'timing' is a guess; first month under on a regular supplier, so too early to tell."),
    "2026-03_4040_Administration": (A, "",
        "Correct: one network maintenance invoice from Odense IT-Drift ApS (DKK 0,14m) is larger than the whole variance, so 'one-off' fits."),
    "2026-03_4050_Sales": (X,
        "Marketing was DKK 0,08m (58,4 %) over budget. Kommunikationshuset Fyn ApS invoiced DKK 0,14m for product "
        "brochures, against DKK 0,04m on average in the previous three months, more than the whole variance. "
        "One brochure invoice drives it, so it looks one-off.",
        "AI wrong: says Kommunikationshuset explains about half, but its increase is larger than the whole variance."),
    # ---------------------------------------------------------------- 2026-02
    "2026-02_4040_Administration": (A, "",
        "Correct: one DataPunkt Hosting invoice (DKK 0,11m) is larger than the whole variance, so 'one-off' fits."),
    "2026-02_4090_Administration": (A, "",
        "Correct: several suppliers and lines without a counterparty rose, and no persistence claim is made."),
    "2026-02_4050_Sales": (E,
        "Marketing was DKK 0,05m (38,5 %) under budget. Kommunikationshuset Fyn ApS invoiced nothing, against "
        "DKK 0,09m on average in the previous three months. January was over budget, " + TOO_EARLY_DOWN,
        "Added context: a missing invoice from a regular supplier is not one transaction; first month under, so too early to tell."),
    # ---------------------------------------------------------------- 2026-01
    "2026-01_4010_Production": (A, "",
        "Correct: one preventive maintenance invoice from Fynsk Maskinreparation (DKK 0,20m) is larger than the whole variance, so 'one-off' fits."),
    "2026-01_4050_Sales": (A, "",
        "Correct: both Kommunikationshuset Fyn and Messepartner Danmark rose, and no persistence claim is made."),
    # ---------------------------------------------------------------- 2025-12 .. 2025-10
    "2025-12_4050_Sales": (A, "",
        "Correct: both main suppliers invoiced less, and no persistence claim is made."),
    "2025-12_4010_Production": (X,
        "Repairs and maintenance were DKK 0,05m (19,6 %) under budget. Hydra-Service Danmark ApS invoiced "
        "DKK 0,05m, against DKK 0,18m on average in the previous three months, while Fynsk Maskinreparation ApS "
        "invoiced more. November was over budget, " + TOO_EARLY_DOWN,
        "AI wrong: says no supplier explains half, but the drop at Hydra-Service Danmark ApS is larger than the whole variance."),
    "2025-11_4050_Sales": (A, "",
        "Correct: one online campaign invoice from Kommunikationshuset Fyn (DKK 0,14m) is larger than the whole variance, so 'one-off' fits."),
    "2025-11_4010_Production": (A, "",
        "Correct: two suppliers rose while a third fell, so no single cause, and no persistence claim is made."),
    "2025-10_4050_Sales": (E,
        "Marketing was DKK 0,09m (69,1 %) under budget. Kommunikationshuset Fyn ApS invoiced nothing, against "
        "DKK 0,11m on average in the previous three months. September was slightly under budget too; the ledger "
        "does not show why the supplier has not invoiced.",
        "Added context: driver is right, but 'timing' is a guess that the ledger does not support."),
    # ---------------------------------------------------------------- 2025-09 .. 2025-07
    "2025-09_4010_Production": (A, "",
        "Correct: Hydra-Service drives it and the months before were also over budget; the cause label 'price' is wrong but not in the text."),
    "2025-09_4040_Administration": (A, "",
        "Correct: Nordlys Software licences drive it and July and August were also over budget."),
    "2025-09_4090_Administration": (A, "",
        "Correct: two suppliers rose, so no single cause, and no persistence claim is made."),
    "2025-08_4010_Production": (A, "",
        "Correct: Hydra-Service drives it and the months before were also over budget."),
    "2025-08_4040_Administration": (E,
        "IT costs were DKK 0,10m (65,8 %) over budget. Odense IT-Drift ApS invoiced DKK 0,09m against DKK 0,03m "
        "on average in the previous three months, and Nordlys Software A/S and DataPunkt Hosting ApS also invoiced "
        "more. July was close to budget, " + TOO_EARLY_UP,
        "Added context: no single invoice is larger than the variance and three suppliers rose, so 'one-off' is not supported."),
    "2025-08_4050_Sales": (A, "",
        "Correct: one trade fair invoice from Messepartner Danmark (DKK 0,15m) is larger than the whole variance, so 'one-off' fits."),
    "2025-07_4010_Production": (A, "",
        "Correct: one electrical service invoice from ElektroTeknik Tarup (DKK 0,15m) is larger than the whole variance, so 'one-off' fits."),
    "2025-07_4050_Sales": (A, "",
        "Correct: one brochure invoice from Kommunikationshuset Fyn (DKK 0,16m) is larger than the whole variance, so 'not persistent' fits."),
    # ---------------------------------------------------------------- 2025-06 .. 2025-04
    "2025-06_4040_Administration": (A, "",
        "Correct: two suppliers invoiced less, so no single cause, and no persistence claim is made."),
    "2025-06_4010_Production": (A, "",
        "Correct: one spare parts invoice from Fynsk Maskinreparation (DKK 0,11m) is larger than the whole variance, so 'one-off' fits."),
    "2025-06_4090_Administration": (E,
        "Other external costs were DKK 0,06m (70,0 %) under budget. Costs were lower across several suppliers and "
        "lines without a counterparty, with no single driver. May was over budget, " + TOO_EARLY_DOWN,
        "Added context: 'timing' is a guess on many running lines in the first month under budget."),
    "2025-06_4050_Sales": (E,
        "Marketing was DKK 0,06m (48,2 %) under budget. Messepartner Danmark ApS invoiced nothing, against "
        "DKK 0,03m on average in the previous three months. May was also under budget.",
        "Added context: driver is right, but 'timing and one-off' is a guess, and May was also under budget."),
    "2025-05_4010_Production": (A, "",
        "Correct: one spare parts invoice from Fynsk Maskinreparation (DKK 0,11m) is larger than the whole variance, so 'one-off' fits."),
    "2025-05_4060_Sales": (A, "",
        "Correct: Nordrejser Erhverv drives it and the months before were also over budget; the cause label 'price' is not in the text."),
    "2025-05_4090_Administration": (A, "",
        "Correct: several suppliers and lines without a counterparty rose, and no persistence claim is made."),
    "2025-04_4040_Administration": (E,
        "IT costs were DKK 0,10m (65,8 %) over budget. Nordlys Software A/S invoiced DKK 0,15m for Microsoft 365 "
        "and ERP licences, against DKK 0,04m on average in the previous three months. March was under budget, " + TOO_EARLY_UP,
        "Added context: driver is right, but no single invoice is larger than the variance; first month over, so too early to tell."),
    "2025-04_4050_Sales": (A, "",
        "Correct: both main suppliers rose, so no single cause, and no persistence claim is made."),
    "2025-04_4010_Production": (E,
        "Repairs and maintenance were DKK 0,05m (20,2 %) under budget, the fourth month in a row. Hydra-Service "
        "Danmark ApS invoiced nothing, against DKK 0,08m on average in the previous three months, while ElektroTeknik "
        "Tarup ApS invoiced DKK 0,15m more than its average.",
        "Added context: the draft misses that this is the fourth month under budget; the labels say unclear but persistent."),
    # ---------------------------------------------------------------- 2025-03 .. 2024-10
    "2025-03_4050_Sales": (E,
        "Marketing was DKK 0,11m (85,6 %) under budget. Messepartner Danmark ApS invoiced DKK 0,01m, against "
        "DKK 0,07m on average in the previous three months, and Kommunikationshuset Fyn ApS also invoiced less. "
        "February was also under budget.",
        "Added context: driver is right, but 'timing' is a guess, and February was also under budget."),
    "2025-02_4050_Sales": (E,
        "Marketing was DKK 0,11m (85,6 %) under budget. Messepartner Danmark ApS invoiced nothing, against "
        "DKK 0,10m on average in the previous three months. January was also under budget; the ledger does not show why.",
        "Added context: driver is right, but 'activity shifts to other months' is not in the ledger."),
    "2025-02_4010_Production": (A, "",
        "Correct: lower Hydra-Service costs drive most of it, and the persistence is left open."),
    "2025-01_4010_Production": (A, "",
        "Correct: no supplier explains half of the variance, and no persistence claim is made."),
    "2025-01_4040_Administration": (E,
        "IT costs were DKK 0,09m (57,2 %) under budget. Nordlys Software A/S invoiced DKK 0,01m, against DKK 0,11m "
        "on average in the previous three months. December was only slightly under budget, " + TOO_EARLY_DOWN,
        "Added context: driver is right, but 'timing' is a guess in the first material month under budget."),
    "2025-01_4050_Sales": (E,
        "Marketing was DKK 0,06m (48,4 %) under budget. Kommunikationshuset Fyn ApS invoiced DKK 0,03m, against "
        "DKK 0,09m on average in the previous three months, and Messepartner Danmark ApS also invoiced less. "
        "December was over budget, " + TOO_EARLY_DOWN,
        "Added context: 'activity is expected to pick up' is a forecast the ledger does not support; first month under, so too early to tell."),
    "2024-12_4050_Sales": (A, "",
        "Correct: one trade fair invoice from Messepartner Danmark (DKK 0,16m) is larger than the whole variance, so 'one-off' fits."),
    "2024-11_4010_Production": (E,
        "Repairs and maintenance were DKK 0,16m (62,0 %) under budget. ElektroTeknik Tarup ApS invoiced nothing, "
        "against DKK 0,08m in October, and spend was low across all suppliers. October was also under budget; the "
        "ledger does not show why.",
        "Added context: 'postponed maintenance work' is not in the ledger, and October was also under budget."),
    "2024-11_4050_Sales": (A, "",
        "Correct: one trade fair invoice from Messepartner Danmark (DKK 0,10m) is larger than the whole variance, so 'one-off' fits."),
    "2024-11_4040_Administration": (A, "",
        "Correct: one ERP licence invoice from Nordlys Software (DKK 0,15m) is larger than the whole variance, so 'one-off' fits."),
    "2024-10_4010_Production": (A, "",
        "Correct: no supplier explains half of the variance; first month of data, and no persistence claim is made."),
    "2024-10_4090_Administration": (A, "",
        "Correct: no supplier explains half of the variance; first month of data, and no persistence claim is made."),
}

WHY_START = {A: ("Correct:",), E: ("Missed driver:", "Added context:"), X: ("AI wrong:",)}
NEG = re.compile(r"DKK\s*[-−–]\s*\d|(?<![\w.,])[-−–]\d")  # copy of evaluate_ai.sign_error (importing it loads data/truth/)
HEAD = ["variance_id", "period", "account", "cost_centre", "actual", "budget (flexed for price rows)", "variance", "%",
        "top ledger lines", "AI draft (v3a)", "cause", "persistence", "figure check", "flags (sign, consistency)",
        "SUGGESTED status", "SUGGESTED final_comment", "why suggested", "status", "final_comment", "reviewer_note"]
WIDTH = [30, 9, 24, 14, 13, 13, 13, 8, 60, 60, 12, 12, 12, 22, 12, 60, 45, 11, 60, 40]


def sign_error(comment, favourable):
    if NEG.search(comment):
        return "minus sign"
    t = comment.lower()
    u, f = "unfavourabl" in t, re.search(r"(?<!un)favourabl", t) is not None
    if favourable and u and not f:
        return "says unfavourable"
    if not favourable and f and not u:
        return "says favourable"
    return None


def eu(x):
    return f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def controller_has_started():
    """True if the existing workbook already has anything in the controller's three columns."""
    if not WORKBOOK.exists():
        return False
    header, *body = load_workbook(WORKBOOK, read_only=True).active.iter_rows(values_only=True)
    cols = [header.index(c) for c in ("status", "final_comment", "reviewer_note")]
    return any(r[c] not in (None, "") for r in body for c in cols)


def main():
    read = lambda p: json.load(open(ROOT / p, encoding="utf-8"))
    mv = {m["variance_id"]: m for m in read("data/export/material_variances.json")}
    drafts = {d["variance_id"]: d for d in read("data/ai/v3a/drafts.json")}
    gl = list(csv.DictReader(open(ROOT / "data/raw/gl_transactions.csv", encoding="utf-8")))
    reviews = list(csv.DictReader(open(ROOT / "data/ai/reviews.csv", encoding="utf-8")))
    assert all(r["status"] == r["final_comment"] == r["reviewer_note"] == "" for r in reviews), "reviews.csv has work"
    assert not controller_has_started(), f"{WORKBOOK} already has controller input; not overwriting"
    assert set(S) == {r["variance_id"] for r in reviews}, set(S) ^ {r["variance_id"] for r in reviews}
    for vid, (st, fc, why) in S.items():
        assert (st == A) == (fc == ""), vid
        assert why.startswith(WHY_START[st]), vid
        assert len(fc.split()) <= 60, (vid, len(fc.split()))

    wb = Workbook()
    ws = wb.active
    ws.title = "Review"
    ws.append(HEAD)
    for r in reviews:
        vid = r["variance_id"]
        m, d = mv[vid], drafts[vid]
        lines = [g for g in gl if g["period"] == m["period"] and int(g["account_no"]) == m["account_no"]
                 and g["cost_centre"] == m["cost_centre"]]
        lines.sort(key=lambda g: -abs(float(g["amount_dkk"])))
        top = "\n".join(f"{g['posting_date']} | {g['counterparty'] or '(none)'} | {g['description']} | {eu(float(g['amount_dkk']))}"
                        for g in lines[:3])
        fcheck, comment = d["figure_check"], d["output"]["comment"]
        flags = [f"sign: {e}"] if (e := sign_error(comment, m["favourable"])) else []
        flags += [f"consistency: {f}" for f in fcheck["consistency_flags"]]
        budget = m["flexed_budget_dkk"] if m["variance_type"] == "price" else m["budget_dkk"]
        ws.append([vid, m["period"], f"{m['account_no']} {m['account_name']}", m["cost_centre"], m["actual_dkk"], budget,
                   m["variance_profit_dkk"], m["variance_pct"], top, comment, d["output"]["cause_category"],
                   d["output"]["persistence"],
                   "passed" if fcheck["check_passed"] else "failed: " + ", ".join(map(str, fcheck["unmatched"])),
                   "; ".join(flags) or "none", *S[vid], "", "", ""])

    last = ws.max_row
    dv = DataValidation(type="list", formula1='"approved,edited,rejected"', allow_blank=True, showErrorMessage=True,
                        error="Choose approved, edited or rejected (or leave empty).")
    ws.add_data_validation(dv)
    dv.add(f"R2:R{last}")
    sugg_fill, mine_fill = PatternFill("solid", fgColor="FFF2CC"), PatternFill("solid", fgColor="DDEBF7")
    for i, w in enumerate(WIDTH, 1):
        ws.column_dimensions[ws.cell(1, i).column_letter].width = w
    for c in ws[1]:
        c.font = Font(bold=True)
    for row in ws.iter_rows(min_row=1):
        for c in row:
            c.alignment = Alignment(vertical="top", wrap_text=c.column_letter in "IJPQS")
            if c.column_letter in "OPQ":
                c.fill = sugg_fill
            elif c.column_letter in "RST":
                c.fill = mine_fill
        if row[0].row > 1:
            for c in row[4:7]:
                c.number_format = "#,##0"
            row[7].number_format = "0.0"
    ws.freeze_panes = "B2"
    wb.save(WORKBOOK)
    counts = {s: sum(v[0] == s for v in S.values()) for s in (A, E, X)}
    print(f"wrote {WORKBOOK.relative_to(ROOT)}: {last - 1} rows; " + ", ".join(f"{k} {v}" for k, v in counts.items()))


if __name__ == "__main__":
    main()
