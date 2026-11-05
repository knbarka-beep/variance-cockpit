"""Read the controller's review from data/check/review.xlsx back into data/ai/reviews.csv.

Only variance_id, status, final_comment and reviewer_note are written back; the other
columns in the workbook are there to read. reviews.csv keeps its own row order.

Stops with an error, and changes nothing, if:
  - a status is not empty, approved, edited or rejected,
  - a row marked edited has no final_comment,
  - reviewed_by (reviews.csv only) is not empty, claude or knut, or is filled in without a status,
  - a variance_id is blank, or a variance in reviews.csv is missing from the workbook
    (or the workbook has one that reviews.csv does not know).

check_reviews() is also used by build_db.py, so the same rules apply there.

Run:  .venv/Scripts/python scripts/review_import.py
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEWS = ROOT / "data" / "ai" / "reviews.csv"
WORKBOOK = ROOT / "data" / "check" / "review.xlsx"
COLUMNS = ["variance_id", "status", "final_comment", "reviewer_note"]
STATUSES = {"", "approved", "edited", "rejected"}
REVIEWERS = {"", "claude", "knut"}  # reviews.csv only: who set the status


def check_reviews(rows):
    """Return a list of problems with the review rows (empty list = all fine)."""
    problems = []
    for n, r in enumerate(rows, 2):  # row 1 is the header
        vid = r["variance_id"] or f"row {n}"
        if not r["variance_id"]:
            problems.append(f"row {n}: variance_id is missing")
        if r["status"] not in STATUSES:
            problems.append(f"{vid}: status '{r['status']}' is not empty, approved, edited or rejected")
        if r["status"] == "edited" and not r["final_comment"]:
            problems.append(f"{vid}: status is edited but final_comment is empty")
        if r.get("reviewed_by", "") not in REVIEWERS:
            problems.append(f"{vid}: reviewed_by '{r['reviewed_by']}' is not empty, claude or knut")
        if "reviewed_by" in r and bool(r["status"]) != bool(r["reviewed_by"]):
            problems.append(f"{vid}: status and reviewed_by must both be filled in or both be empty")
    return problems


def read_csv():
    with REVIEWS.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def read_workbook():
    from openpyxl import load_workbook
    ws = load_workbook(WORKBOOK, read_only=True).active
    header, *body = ws.iter_rows(values_only=True)
    col = {name: header.index(name) for name in COLUMNS}

    def text(value):
        return "" if value is None else str(value).strip()
    return [{name: text(row[col[name]]) for name in COLUMNS} for row in body if any(v is not None for v in row)]


def main():
    if not WORKBOOK.exists():
        sys.exit(f"{WORKBOOK.relative_to(ROOT)} not found. Run review_export.py first.")
    rows = read_workbook()
    for r in rows:
        r["status"] = r["status"].lower()
    problems = check_reviews(rows)
    in_csv = [r["variance_id"] for r in read_csv()]
    in_xlsx = {r["variance_id"] for r in rows if r["variance_id"]}
    problems += [f"{vid}: in reviews.csv but missing from the workbook" for vid in in_csv if vid not in in_xlsx]
    problems += [f"{vid}: in the workbook but not in reviews.csv" for vid in sorted(in_xlsx - set(in_csv))]
    if problems:
        sys.exit("Review NOT imported, reviews.csv unchanged:\n  " + "\n  ".join(problems))

    by_id = {r["variance_id"]: r | {"reviewed_by": "knut" if r["status"] else ""} for r in rows}
    tmp = REVIEWS.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS + ["reviewed_by"])
        w.writeheader()
        w.writerows(by_id[vid] for vid in in_csv)
    tmp.replace(REVIEWS)
    done = sum(r["status"] != "" for r in rows)
    print(f"Imported {len(rows)} rows into {REVIEWS.relative_to(ROOT)}: {done} reviewed, {len(rows) - done} not yet.")


if __name__ == "__main__":
    main()
