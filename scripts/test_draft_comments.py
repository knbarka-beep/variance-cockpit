"""Self-checks for draft_comments.py: figure check, retries and model fallback (no API calls).
Run: .venv/Scripts/python scripts/test_draft_comments.py"""
from draft_comments import figure_check, parse_figures

values = [(f["value"], f["kind"]) for f in parse_figures(
    "Repairs DKK 236.321 over budget (89,4 %), mainly one invoice of DKK 0,35m; also 236k and 8,9 % in 3 months.")]
assert values == [(236321, "amount"), (89.4, "pct"), (350000, "amount"), (236000, "amount"), (8.9, "pct")], values

inp = {"variance_dkk": -236320.58, "variance_pct": -89.4, "ledger_lines": [
    {"description": "Invoice 48213, emergency repair", "amount_dkk": 350000.0}], "period": "2026-09"}
ok = figure_check("Invoice 48213 of DKK 350.000 drove the DKK 0,24m (89 %) overspend in 2026.", inp)
assert ok["check_passed"] and ok["figures_found"] == 5, ok   # 48213, 350.000, 0,24m, 89 %, and 2026 (from the period)
bad = figure_check("Overspend of DKK 412.000, up 25 %.", inp)
assert bad["unmatched"] == ["DKK 412.000", "25 %"], bad      # invented numbers are caught
english = figure_check("Overspend of DKK 236,321.", inp)
assert not english["check_passed"], english                   # English number format is flagged
print("figure check: all tests passed")

# ---- retry and model fallback in call_gemini (fake client, no API calls)
import draft_comments
from google.genai import errors

def api_error(code, message, details=()):
    return errors.APIError(code, {"error": {"code": code, "message": message, "status": "X", "details": list(details)}})

class FakeClient:
    def __init__(self, outcomes):
        self.outcomes, self.models = list(outcomes), self
    def generate_content(self, **kw):
        o = self.outcomes.pop(0)
        if isinstance(o, Exception):
            raise o
        return type("R", (), {"parsed": o, "text": ""})()

waits = []
draft_comments.time.sleep = waits.append
good = draft_comments.Draft(comment="x", cause_category="unclear", persistence="unknown", figures_cited=[], no_clear_cause=True)

# 503 then per-minute 429 with a retry delay, then success: same model, waits 10s then 34+1s
fake = FakeClient([api_error(503, "busy"), api_error(429, "rate", [{"retryDelay": "34s"}]), good])
assert draft_comments.call_gemini(fake, "m1", {}) is good and waits == [10, 35.0], waits

# daily quota or 'limit: 0' -> ModelUnavailable straight away, no waiting
for msg in ["Quota exceeded ... GenerateRequestsPerDayPerProjectPerModel-FreeTier", "Quota exceeded, limit: 0, model m1"]:
    try:
        draft_comments.call_gemini(FakeClient([api_error(429, msg)]), "m1", {})
        raise SystemExit("expected ModelUnavailable")
    except draft_comments.ModelUnavailable:
        pass

# five busy errors in a row -> gives up after 4 retries (10, 20, 40, 80 s) and marks the model unavailable
waits.clear()
try:
    draft_comments.call_gemini(FakeClient([api_error(504, "deadline")] * 5), "m1", {})
    raise SystemExit("expected ModelUnavailable")
except draft_comments.ModelUnavailable as e:
    assert waits == [10, 20, 40, 80] and "after 4 retries (504)" in str(e), (waits, e)
print("retry and fallback: all tests passed")

# a timeout (no answer within 60 s) is retried like a temporary error
import httpx
waits.clear()
assert draft_comments.call_gemini(FakeClient([httpx.ReadTimeout("slow"), good]), "m1", {}) is good and waits == [10], waits
print("timeout retry: test passed")

# ---- consistency flags (no answer key)
from draft_comments import consistency_flags
ok_out = {"cause_category": "unclear", "persistence": "unknown", "no_clear_cause": True}
assert consistency_flags(ok_out) == []
assert consistency_flags(ok_out | {"persistence": "persistent"}) == ["unclear but persistent"]
assert consistency_flags(ok_out | {"no_clear_cause": False}) == ["no_clear_cause false but cause unclear"]
assert consistency_flags({"cause_category": "price", "persistence": "one_off", "no_clear_cause": True}) == \
    ["no_clear_cause true but cause price"]
print("consistency flags: all tests passed")
