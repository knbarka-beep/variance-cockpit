"""Write data/check/review.xlsx: one row per material variance, for the controller to review.

Rows are in the same order as data/ai/reviews.csv. The AI draft and the variance figures
come from data/export/comments.json (run build_db.py first); status, final_comment and
reviewer_note come from reviews.csv, so earlier review work is shown again.

The controller fills in the last three columns, then runs review_import.py.
It will not overwrite a review.xlsx that holds work not yet imported.

Run:  .venv/Scripts/python scripts/review_export.py
"""
import json
import sys

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.worksheet.datavalidation import DataValidation

from review_import import ROOT, WORKBOOK, read_csv, read_workbook

# Only overwrite a workbook whose review columns match reviews.csv (i.e. already imported).
if WORKBOOK.exists() and read_workbook() != read_csv():
    sys.exit(f"{WORKBOOK.relative_to(ROOT)} holds review work not yet in reviews.csv.\n"
             "Run review_import.py first (or delete the workbook to discard that work).")

comments = {c["variance_id"]: c for c in json.loads((ROOT / "data/export/comments.json").read_text(encoding="utf-8"))}
FROM_COMMENTS = ["variance_id", "period", "account_name", "cost_centre", "variance_profit_dkk", "variance_pct",
                 "ai_comment", "ai_cause_category", "ai_persistence"]
FROM_REVIEWS = ["status", "final_comment", "reviewer_note"]
WIDTHS = [32, 9, 28, 15, 16, 12, 70, 17, 15, 11, 70, 40]

wb = Workbook()
ws = wb.active
ws.title = "Review"
ws.append(FROM_COMMENTS + FROM_REVIEWS)
for review in read_csv():
    c = comments.get(review["variance_id"])
    if c is None:
        sys.exit(f"{review['variance_id']} is in reviews.csv but not in comments.json. Run build_db.py first.")
    ws.append([c[k] for k in FROM_COMMENTS] + [review[k] for k in FROM_REVIEWS])

last = ws.max_row
status = DataValidation(type="list", formula1='"approved,edited,rejected"', allow_blank=True,
                        error="Choose approved, edited or rejected (or leave empty).", showErrorMessage=True)
ws.add_data_validation(status)
status.add(f"J2:J{last}")
for i, width in enumerate(WIDTHS, 1):
    ws.column_dimensions[ws.cell(1, i).column_letter].width = width
for cell in ws[1]:
    cell.font = Font(bold=True)
for row in ws.iter_rows(min_row=2):
    for cell in row:
        cell.alignment = Alignment(vertical="top", wrap_text=cell.column_letter in "GKL")
    row[4].number_format = "#,##0"
    row[5].number_format = "0.0"
ws.freeze_panes = "A2"

WORKBOOK.parent.mkdir(parents=True, exist_ok=True)
wb.save(WORKBOOK)
print(f"Wrote {WORKBOOK.relative_to(ROOT)} ({last - 1} variances). Fill in status, final_comment, reviewer_note,")
print("then run review_import.py.")
