"""Evaluate the AI draft comments against the answer key.

This is the ONLY script that may read data/truth/. It is a first automatic pass;
the controller judges the comments themselves.

Checks:
  1. Planted events: does the draft for each event's variance name the right cause category?
     Event 6 (no clear cause) must also be flagged no_clear_cause = true.
  2. Noise variances (material, but no planted event behind them): which drafts claim a
     specific cause anyway? Possible hallucinations, listed for review.
  3. Figure check pass rate and the 60-word limit.

Run after draft_comments.py:  .venv/Scripts/python scripts/evaluate_ai.py
Writes data/ai/evaluation.json.
"""
import json
from collections import Counter
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
truth = pd.read_csv(ROOT / "data" / "truth" / "planted_events.csv", dtype=str)
drafts = {d["variance_id"]: d for d in json.loads((ROOT / "data" / "ai" / "drafts.json").read_text(encoding="utf-8"))}
con = duckdb.connect(str(ROOT / "data" / "variance.duckdb"), read_only=True)
material = con.execute("SELECT variance_id, cell_id FROM v_material_variances ORDER BY variance_id").fetchall()
con.close()
if not drafts:
    raise SystemExit("No drafts yet. Run scripts/draft_comments.py first.")

# ---------------------------------------------------------------- 1. planted events
events, event_cells = [], set()
for e in truth.itertuples():
    suffix = "_price" if e.check_basis == "flexed budget" else ""
    results = []
    for period in e.periods.split(";"):
        for account in e.accounts.split(";"):
            cell = f"{period}_{account}_{e.cost_centre}"
            event_cells.add(cell)
            vid = cell + suffix
            out = drafts.get(vid, {}).get("output")
            ok = (out is not None and out["cause_category"] == e.expected_cause_category
                  and (e.expected_cause_category != "unclear" or out["no_clear_cause"]))
            results.append({"variance_id": vid, "drafted": out is not None,
                            "cause_category": out and out["cause_category"],
                            "no_clear_cause": out and out["no_clear_cause"], "correct": ok})
    events.append({"event_id": int(e.event_id), "expected_cause_category": e.expected_cause_category,
                   "variances": results, "correct": sum(r["correct"] for r in results), "total": len(results)})

# ---------------------------------------------------------------- 2. noise variances
noise = [vid for vid, cell in material if cell not in event_cells]
claims = []
for vid in noise:
    out = drafts.get(vid, {}).get("output")
    if out and (out["cause_category"] != "unclear" or not out["no_clear_cause"]):
        claims.append({"variance_id": vid, "cause_category": out["cause_category"],
                       "no_clear_cause": out["no_clear_cause"], "comment": out["comment"]})

# ---------------------------------------------------------------- 3. figure check and length
checks = [d["figure_check"] for d in drafts.values()]
figure_pass = sum(c["check_passed"] for c in checks)
words_ok = sum(c["word_count"] <= 60 for c in checks)

per_model = dict(Counter(d["model"] for d in drafts.values()).most_common())

evaluation = {
    "drafts": len(drafts), "material_variances": len(material), "drafts_per_model": per_model,
    "planted_events": events,
    "noise_variances": len(noise),
    "noise_drafts_claiming_a_cause": len(claims),
    "noise_claims_for_review": claims,
    "figure_check_passed": figure_pass,
    "figure_check_failed": [{"variance_id": d["variance_id"], "unmatched": d["figure_check"]["unmatched"]}
                            for d in drafts.values() if not d["figure_check"]["check_passed"]],
    "within_60_words": words_ok,
}
(ROOT / "data" / "ai" / "evaluation.json").write_text(json.dumps(evaluation, indent=2, ensure_ascii=False) + "\n",
                                                       encoding="utf-8")

# ---------------------------------------------------------------- print
print(f"\nAI evaluation - {len(drafts)} drafts for {len(material)} material variances")
print("Drafts per model: " + ", ".join(f"{m} {n}" for m, n in per_model.items()) + "\n")
print(f"{'Event':<7}{'Expected':<11}{'Correct':>8}  Drafts (category)")
for e in events:
    detail = ", ".join(f"{r['variance_id']}={r['cause_category']}" + ("" if r["correct"] else " X")
                       for r in e["variances"])
    print(f"{e['event_id']:<7}{e['expected_cause_category']:<11}{e['correct']:>4}/{e['total']:<3}  {detail}")
total_ok = sum(e["correct"] for e in events)
total_n = sum(e["total"] for e in events)
print(f"{'All':<18}{total_ok:>4}/{total_n}")
print(f"\nNoise variances: {len(noise)}; drafts claiming a specific cause: {len(claims)} (review these)")
for c in claims:
    print(f"  {c['variance_id']:<34}{c['cause_category']:<10}{c['comment']}")
print(f"\nFigure check passed: {figure_pass}/{len(checks)} ({figure_pass / len(checks):.0%})")
for f in evaluation["figure_check_failed"]:
    print(f"  {f['variance_id']:<34}unmatched: {', '.join(f['unmatched'])}")
print(f"Within 60 words:     {words_ok}/{len(checks)}")
print("\nWritten to data/ai/evaluation.json")
