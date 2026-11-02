"""Tests the review status rules (no files touched).  Run: .venv/Scripts/python scripts/test_review.py"""
from review_import import check_reviews


def row(vid="2026-09_1010_Sales", status="", final="", note=""):
    return {"variance_id": vid, "status": status, "final_comment": final, "reviewer_note": note}


assert check_reviews([row(), row(status="approved"), row(status="rejected"), row(status="edited", final="New")]) == []
assert check_reviews([row(status="ok")]) == ["2026-09_1010_Sales: status 'ok' is not empty, approved, edited or rejected"]
assert check_reviews([row(status="edited")]) == ["2026-09_1010_Sales: status is edited but final_comment is empty"]
assert check_reviews([row(vid="")]) == ["row 2: variance_id is missing"]
print("review rules: all tests passed")
