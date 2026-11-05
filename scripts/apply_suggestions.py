"""Write Claude's suggested review (scripts/review_suggestions.py) into data/ai/reviews.csv.

status = Claude's suggested status, final_comment = the suggested text (empty when approved),
reviewer_note = why it was suggested, reviewed_by = "claude". A row already marked
reviewed_by = "knut" is never changed. Validated with the same rules as build_db.py.

Run:  .venv/Scripts/python scripts/apply_suggestions.py
"""
import csv
import sys

from review_import import COLUMNS, REVIEWS, check_reviews, read_csv
from review_suggestions import S


def main():
    old = read_csv()
    assert {r["variance_id"] for r in old} == set(S), "reviews.csv and the suggestions cover different variances"
    new = []
    for r in old:
        if r.get("reviewed_by") == "knut":
            new.append(r)
            continue
        st, final, why = S[r["variance_id"]]
        new.append({"variance_id": r["variance_id"], "status": st, "final_comment": final,
                    "reviewer_note": why, "reviewed_by": "claude"})
    if problems := check_reviews(new):
        sys.exit("Not written:\n  " + "\n  ".join(problems))
    with REVIEWS.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS + ["reviewed_by"])
        w.writeheader()
        w.writerows(new)
    by = {s: sum(r["status"] == s for r in new) for s in ("approved", "edited", "rejected")}
    print(f"wrote {len(new)} rows: {by}; knut rows kept: {sum(r['reviewed_by'] == 'knut' for r in new)}")


if __name__ == "__main__":
    main()
