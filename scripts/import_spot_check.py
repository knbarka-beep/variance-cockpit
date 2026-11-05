"""Import Knut's spot check (data/check/spot_check.xlsx) into data/ai/reviews.csv.

For the 18 sampled rows: reviewed_by = "knut". Where Agree = Yes, Claude's status stays.
Where Agree = No, Knut's status replaces Claude's; the final_comment and reviewer_note for
those rows are written below (KNUT), in English, from Knut's notes in the sheet.
A new final_comment gets the same checks as Claude's suggestions (check_suggestions.py):
figures against the AI input and the account's history up to that month, no look-ahead,
British spelling, at most 60 words. The rule for reporting is in docs/decisions.md.
Stops and changes nothing if a check fails or the sheet does not match KNUT.

Run:  .venv/Scripts/python scripts/import_spot_check.py
"""
import csv
import sys

import duckdb
from openpyxl import load_workbook

from check_suggestions import history, look_ahead, parties, text_problems
from draft_comments import ROOT, build_input, figure_check, rows
from review_import import COLUMNS, REVIEWS, check_reviews, read_csv

SHEET = ROOT / "data" / "check" / "spot_check.xlsx"

# Rows where Knut disagreed: (status, final_comment, reviewer_note).
KNUT = {
    "2025-02_4010_Production": (
        "edited",
        "Repairs and maintenance was DKK 0,10m under budget. Hydra-Service Danmark ApS invoiced DKK 0,06m less than "
        "its three-month average, but ElektroTeknik Tarup ApS invoiced DKK 0,06m more, so total spend was close to "
        "recent months. The account was also under budget in two of the previous three months.",
        "Missed driver: an offsetting increase at ElektroTeknik Tarup ApS. Found in Knut's spot check; Claude had approved it."),
    "2026-09_3030_Production": (
        "approved", "",
        "Correct: approved in Knut's spot check; Claude had marked it edited for spelling."),
}


def read_sheet():
    all_rows = list(load_workbook(SHEET, read_only=True).active.iter_rows(values_only=True))
    h = next(i for i, r in enumerate(all_rows) if r and r[0] == "variance_id")
    col = {name: all_rows[h].index(name) for name in ("variance_id", "Agree", "Knut status")}
    return {r[col["variance_id"]]: ((r[col["Agree"]] or "").strip(), (r[col["Knut status"]] or "").strip())
            for r in all_rows[h + 1:] if r[0]}


def main():
    sheet = read_sheet()
    problems = [f"{vid}: Agree is '{a}'" for vid, (a, _) in sheet.items() if a not in ("Yes", "No")]
    no = {vid: st for vid, (a, st) in sheet.items() if a == "No"}
    if {vid: KNUT[vid][0] for vid in KNUT} != no:
        problems.append(f"disagreements in the sheet {no} do not match KNUT in this script")
    con = duckdb.connect(str(ROOT / "data" / "variance.duckdb"), read_only=True)
    for vid, (st, text, _) in KNUT.items():
        if text:
            v = rows(con, "SELECT * FROM v_material_variances WHERE variance_id = ?", [vid])[0]
            hist = history(con, v)
            ctx = {"history": list(hist.values()), "parties": parties(con, v)}
            fc = figure_check(text, build_input(con, v) | {"controller_context": ctx})
            problems += [f"{vid}: figure not in the inputs: {u}" for u in fc["unmatched"]]
            problems += [f"{vid}: {p}" for p in look_ahead(text, v["period"], hist) + text_problems(text)]
    con.close()

    reviews = read_csv()
    for r in reviews:
        if r["variance_id"] in sheet:
            r["reviewed_by"] = "knut"
            if r["variance_id"] in KNUT:
                r["status"], r["final_comment"], r["reviewer_note"] = KNUT[r["variance_id"]]
    problems += check_reviews(reviews)
    if problems or len(sheet) != 18:
        sys.exit(f"Not imported ({len(sheet)} rows in the sheet):\n  " + "\n  ".join(problems))
    with REVIEWS.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS + ["reviewed_by"])
        w.writeheader()
        w.writerows(reviews)
    by = {s: sum(r["status"] == s for r in reviews) for s in ("approved", "edited", "rejected")}
    print(f"Agree: {len(sheet) - len(no)} of {len(sheet)}. Disagreements: {no}")
    print(f"reviews.csv: {by}, total {sum(by.values())}; knut {sum(r['reviewed_by'] == 'knut' for r in reviews)}")


if __name__ == "__main__":
    main()
