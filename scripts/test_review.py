"""Tests the review status rules (no files touched).  Run: .venv/Scripts/python scripts/test_review.py"""
from review_import import check_reviews


def row(vid="2026-09_1010_Sales", status="", final="", note=""):
    return {"variance_id": vid, "status": status, "final_comment": final, "reviewer_note": note}


assert check_reviews([row(), row(status="approved"), row(status="rejected"), row(status="edited", final="New")]) == []
assert check_reviews([row(status="ok")]) == ["2026-09_1010_Sales: status 'ok' is not empty, approved, edited or rejected"]
assert check_reviews([row(status="edited")]) == ["2026-09_1010_Sales: status is edited but final_comment is empty"]
assert check_reviews([row(vid="")]) == ["row 2: variance_id is missing"]
by = lambda st, who: row(status=st) | {"reviewed_by": who}
assert check_reviews([by("approved", "claude"), by("rejected", "knut"), by("", "")]) == []
assert check_reviews([by("approved", "gemini")]) == ["2026-09_1010_Sales: reviewed_by 'gemini' is not empty, claude or knut"]
assert check_reviews([by("approved", "")]) == ["2026-09_1010_Sales: status and reviewed_by must both be filled in or both be empty"]
print("review rules: all tests passed")
