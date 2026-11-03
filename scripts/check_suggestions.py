"""Check the SUGGESTED review columns in data/check/review.xlsx before the controller reads them.

The suggestions are written by Claude, so they get the same kind of checks as the AI drafts:

  a) Figure check: every figure must match a number the controller has at close for that row:
     the AI input (draft_comments.build_input) plus the same account's history up to and
     including the month (actual, budget, flexed budget, variance, %), and each customer's or
     supplier's monthly total up to that month. Nothing from later months.
  b) Look-ahead: a month later than the row, or phrases like "next month"; words such as
     "continued", "remained", "persisted", "again in" need the month before to point the same
     way; claims like "May was also over budget", "third month in a row" and "first month under"
     are checked against the ledger.
  c) American spelling (favorable, unfavorable, analyze, labor, organization, ...).
  d) More than 60 words, or Cause / Persistence labels in the text.

Rows marked approved have no suggested text; their AI draft gets checks c) and d).
Exits with code 1 if anything fails. Never reads data/truth/ (draft_comments blocks it).

Run:  .venv/Scripts/python scripts/check_suggestions.py
"""
import re
import sys

import duckdb
from openpyxl import load_workbook

from draft_comments import ROOT, build_input, figure_check, rows

WORKBOOK = ROOT / "data" / "check" / "review.xlsx"
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august",
          "september", "october", "november", "december"]
ORDINAL = {"second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6}
AMERICAN = re.compile(r"\b(un)?favor(able|ably)?\b|\banalyz|\blabor\b|\borganiz|\bbehavior|\bcolor\b|\bcenter\b", re.I)
LABEL = re.compile(r"\b(cause|persistence|cause_category)\s*:|\bone_off\b|\bno_clear_cause\b", re.I)
AHEAD_PHRASE = re.compile(r"\bnext month|\bfollowing month|\blater month|\bsubsequent|\bin the coming|\bwill continue", re.I)
NEEDS_PRIOR = re.compile(r"\b(continued|continues|remained|remains|persisted|persists|again in|still)\b", re.I)
MAX_WORDS = 60


def shift(period, n):
    y, m = map(int, period.split("-"))
    m += n
    return f"{y + (m - 1) // 12}-{(m - 1) % 12 + 1:02d}"


def month_back(period, name):
    """A month name without a year means its latest occurrence up to the row's month."""
    target, p = MONTHS.index(name) + 1, period
    while int(p[5:]) != target:
        p = shift(p, -1)
    return p


def direction(h):
    """'over' if actual is above budget, else 'under' (materiality is checked separately)."""
    return "over" if h["actual"] > h["budget"] else "under"


def matches(said, h):
    """'on' / 'close to' budget = not material; 'over' / 'under' = the sign; 'slightly' allows either."""
    if said == "on":
        return not h["material"]
    if said.endswith("_or_on"):
        return direction(h) == said[:-6] or not h["material"]
    return direction(h) == said


def history(con, v):
    """The account's months up to and including the row's month, on the row's basis."""
    if v["variance_type"] == "price":
        sql = """SELECT period, actual_dkk AS actual, flexed_budget_dkk AS budget, budget_dkk AS plain_budget,
                        flexed_budget_dkk, volume_pct_of_budget, price_usage_variance_profit_dkk AS variance,
                        price_usage_variance_pct AS pct, price_usage_material AS material
                 FROM v_flexed_budget WHERE account_no = ? AND cost_centre = ? AND period <= ? ORDER BY period"""
    else:
        sql = """SELECT period, actual_dkk AS actual, budget_dkk AS budget, variance_profit_dkk AS variance,
                        variance_pct AS pct, material
                 FROM v_account_month WHERE account_no = ? AND cost_centre = ? AND period <= ? ORDER BY period"""
    return {h["period"]: h for h in rows(con, sql, [v["account_no"], v["cost_centre"], v["period"]])}


def parties(con, v):
    keys = [v["account_no"], v["cost_centre"], v["period"]]
    return (rows(con, """SELECT period, cost_dkk, avg_prev_3_months_dkk FROM v_counterparty_month
                         WHERE account_no = ? AND cost_centre = ? AND period <= ?""", keys)
            + rows(con, """SELECT period, revenue_dkk, avg_prev_3_months_dkk FROM v_customer_month
                           WHERE account_no = ? AND cost_centre = ? AND period <= ?""", keys))


def said_direction(sentence):
    """What a sentence says about a month: 'over', 'under', 'on', 'over_or_on', 'under_or_on' or None."""
    for pattern, said in [(r"\bslightly (over|above)", "over_or_on"), (r"\bslightly (under|below)", "under_or_on"),
                          (r"\b(on|close to)( the flexed)? budget", "on"),
                          (r"\b(over|above)\b", "over"), (r"\b(under|below)\b", "under")]:
        if re.search(pattern, sentence):
            return said
    return None


def look_ahead(text, period, hist):
    problems = []
    for name, year in re.findall(r"\b(" + "|".join(MONTHS) + r")\s+(\d{4})\b", text, re.I):
        if f"{year}-{MONTHS.index(name.lower()) + 1:02d}" > period:
            problems.append(f"names a later month: {name} {year}")
    for ym in re.findall(r"\b(20\d\d-\d\d)\b", text):
        if ym > period:
            problems.append(f"names a later month: {ym}")
    if m := AHEAD_PHRASE.search(text):
        problems.append(f"looks ahead: '{m.group(0)}'")
    prev = hist.get(shift(period, -1))
    now = direction(hist[period])
    for sentence in re.split(r"(?<=[.;])\s+", text):
        s = sentence.lower()
        if (m := NEEDS_PRIOR.search(sentence)) and not (prev and direction(prev) == now):
            problems.append(f"'{m.group(0)}' but the month before does not point the same way")
        if m := re.search(r"\b(" + "|".join(ORDINAL) + r")\s+(?:material\s+)?month in a row", s):
            n, run, p = ORDINAL[m.group(1)], 0, period
            while p in hist and direction(hist[p]) == now:
                run, p = run + 1, shift(p, -1)
            if run < n:
                problems.append(f"says {m.group(1)} month in a row, ledger shows {run}")
        if re.search(r"\bfirst month (over|under|below|above)", s) and prev and direction(prev) == now and prev["material"]:
            problems.append("says first month, but the month before was materially the same way")
        said = said_direction(s)
        months = [month_back(period, x.lower()) for x in re.findall(r"\b(" + "|".join(MONTHS) + r")\b", sentence, re.I)]
        months = [p for p in months if p != period]
        if said and months and re.search(r"\b(was|were)\b", s):
            for p in months:
                if p not in hist or not matches(said, hist[p]):
                    actual = f"{direction(hist[p])}, {hist[p]['pct']} %" if p in hist else "missing"
                    problems.append(f"says {p} was {said.replace('_', ' ')} budget, ledger: {actual}")
    return problems


def text_problems(text):
    problems = []
    if m := AMERICAN.search(text):
        problems.append(f"American spelling: '{m.group(0)}'")
    if m := LABEL.search(text):
        problems.append(f"label in text: '{m.group(0)}'")
    if (n := len(text.split())) > MAX_WORDS:
        problems.append(f"{n} words (max {MAX_WORDS})")
    return problems


def selftest():
    assert text_problems("an unfavorable labor cost") and not text_problems("an unfavourable labour cost")
    assert text_problems("Cause: price.") and text_problems("word " * 61) == ["61 words (max 60)"]
    h = {"2026-08": {"actual": 2, "budget": 1, "material": True, "pct": -100},
         "2026-09": {"actual": 2, "budget": 1, "material": True, "pct": -100}}
    assert look_ahead("Costs remained high. August was also over budget.", "2026-09", h) == []
    assert look_ahead("It will continue in October 2026.", "2026-09", h)
    assert look_ahead("August was under budget.", "2026-09", h)
    assert look_ahead("This is the third month in a row.", "2026-09", h)
    assert month_back("2026-01", "december") == "2025-12"


def main():
    selftest()
    ws = load_workbook(WORKBOOK, read_only=True).active
    header, *body = ws.iter_rows(values_only=True)
    col = {name: header.index(name) for name in header if name}
    con = duckdb.connect(str(ROOT / "data" / "variance.duckdb"), read_only=True)
    variances = {v["variance_id"]: v for v in rows(con, "SELECT * FROM v_material_variances")}
    failed = checked = 0
    for r in body:
        vid = r[col["variance_id"]]
        if not vid:
            continue
        status = (r[col["SUGGESTED status"]] or "").strip()
        text = (r[col["SUGGESTED final_comment"]] or "").strip()
        if not status:
            continue
        v = variances[vid]
        problems = []
        if status not in ("approved", "edited", "rejected"):
            problems.append(f"status '{status}'")
        if (status == "approved") != (text == ""):
            problems.append("approved needs an empty final_comment, edited/rejected need one")
        if status == "approved":
            problems += [f"AI draft: {p}" for p in text_problems(r[col["AI draft (v3a)"]] or "")]
        else:
            hist = history(con, v)
            context = {"history": list(hist.values()), "parties": parties(con, v)}
            fc = figure_check(text, build_input(con, v) | {"controller_context": context})
            problems += [f"figure not in the inputs: {u}" for u in fc["unmatched"]]
            problems += look_ahead(text, v["period"], hist) + text_problems(text)
        checked += 1
        if problems:
            failed += 1
            print(f"FAIL {vid}\n     " + "\n     ".join(problems))
    con.close()
    print(f"\n{checked} suggestions checked, {failed} failed.")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
