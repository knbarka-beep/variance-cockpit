"""Evaluate the AI draft comments against the answer key, v1 and v2 side by side.

This is the ONLY script that may read data/truth/. It is a first automatic pass;
the controller judges the comments themselves.

  v1 = data/ai/v1/drafts.json (baseline: first prompt, mixed models)
  v2 = drafts in data/ai/drafts.json with prompt_version "v2"

Measures per version:
  1. Planted events: does the draft name the expected cause category?
     Event 6 (no clear cause) must also be flagged no_clear_cause = true.
  2. Noise variances (material, no planted event behind them). Two measures:
     - false claims (main measure): cause_category "price" or persistence "persistent",
       or the comment names a counterparty or invoice number that is not behind the
       variance in the data. Naming the supplier or invoice that really drives it, as
       one_off or timing, is a correct reading of the ledger and does not count.
     - strict (kept for comparison): any specific cause at all (not 'unclear').
  3. Figure check pass rate (every number in the comment found in the input).
  4. Sign errors: an amount written with a minus sign, or 'favourable' / 'unfavourable'
     used the wrong way round.

Run:  .venv/Scripts/python scripts/evaluate_ai.py     Writes data/ai/evaluation.json.
"""
import json
import re
from collections import Counter
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "data" / "ai"
truth = pd.read_csv(ROOT / "data" / "truth" / "planted_events.csv", dtype=str)
con = duckdb.connect(str(ROOT / "data" / "variance.duckdb"), read_only=True)
material = {vid: (cell, fav) for vid, cell, fav in
            con.execute("SELECT variance_id, cell_id, favourable FROM v_material_variances").fetchall()}
# What is really behind each variance: counterparties and invoice numbers of its ledger lines,
# plus the customers/suppliers in its baseline table (a supplier that dropped to zero has no line).
behind = {}
for cell, counterparty, description in con.execute("""
        SELECT cell_id, counterparty, description FROM v_transactions
        UNION ALL
        SELECT concat_ws('_', period, account_no, cost_centre), customer, NULL FROM v_customer_month
        UNION ALL
        SELECT concat_ws('_', period, account_no, cost_centre), counterparty, NULL FROM v_counterparty_month
        WHERE cost_dkk <> 0 OR avg_prev_3_months_dkk <> 0""").fetchall():
    names, invoices = behind.setdefault(cell, (set(), set()))
    if counterparty:
        names.add(counterparty)
    invoices.update(re.findall(r"Invoice (\d+)", description or ""))
all_counterparties = [r[0] for r in con.execute("SELECT counterparty FROM counterparties").fetchall()]
con.close()
LEGAL_FORM = re.compile(r"\s+(A/S|ApS|GmbH|AB|AS|B\.V\.|Oy|UAB|& Co)$")


def load(path, version=None):
    if not path.exists():
        return {}
    drafts = json.loads(path.read_text(encoding="utf-8"))
    return {d["variance_id"]: d for d in drafts if version is None or d.get("prompt_version") == version}


NEGATIVE_AMOUNT = re.compile(r"DKK\s*[-−–]\s*\d|(?<![\w.,])[-−–]\d")


def sign_error(comment, favourable):
    """Minus sign in front of an amount, or the direction word contradicts the data."""
    if NEGATIVE_AMOUNT.search(comment):
        return "minus sign"
    text = comment.lower()
    says_unfav = "unfavourabl" in text
    says_fav = re.search(r"(?<!un)favourabl", text) is not None
    if favourable and says_unfav and not says_fav:
        return "says unfavourable"
    if not favourable and says_fav and not says_unfav:
        return "says favourable"
    return None


def false_claim(output, cell):
    """Reasons why a noise draft makes a false claim (empty list = no false claim)."""
    reasons = []
    if output["cause_category"] == "price":
        reasons.append("cause price")
    if output["persistence"] == "persistent":
        reasons.append("persistent")
    text = output["comment"].lower()
    names, invoices = behind.get(cell, (set(), set()))
    for name in all_counterparties:  # matched without the legal form, e.g. 'Hydra-Service Danmark'
        if LEGAL_FORM.sub("", name).lower() in text and name not in names:
            reasons.append(f"names {name}, not behind this variance")
    for number in re.findall(r"invoice (\d+)", text):
        if number not in invoices:
            reasons.append(f"invoice {number} not in the ledger lines")
    return reasons


def evaluate(drafts):
    events, event_cells = [], set()
    for e in truth.itertuples():
        suffix = "_price" if e.check_basis == "flexed budget" else ""
        results = []
        for period in e.periods.split(";"):
            for account in e.accounts.split(";"):
                cell = f"{period}_{account}_{e.cost_centre}"
                event_cells.add(cell)
                out = drafts.get(cell + suffix, {}).get("output")
                ok = (out is not None and out["cause_category"] == e.expected_cause_category
                      and (e.expected_cause_category != "unclear" or out["no_clear_cause"]))
                results.append({"variance_id": cell + suffix, "cause_category": out and out["cause_category"],
                                "correct": ok})
        events.append({"event_id": int(e.event_id), "expected": e.expected_cause_category,
                       "correct": sum(r["correct"] for r in results), "total": len(results), "variances": results})

    noise = [vid for vid, (cell, _) in material.items() if cell not in event_cells]
    claims = [{"variance_id": vid, "cause_category": d["output"]["cause_category"], "comment": d["output"]["comment"]}
              for vid in sorted(noise) if (d := drafts.get(vid))
              and (d["output"]["cause_category"] != "unclear" or not d["output"]["no_clear_cause"])]
    false_claims = [{"variance_id": vid, "reasons": reasons, "comment": d["output"]["comment"]}
                    for vid in sorted(noise) if (d := drafts.get(vid))
                    and (reasons := false_claim(d["output"], material[vid][0]))]
    signs = [{"variance_id": vid, "error": err, "comment": d["output"]["comment"]}
             for vid, d in sorted(drafts.items())
             if vid in material and (err := sign_error(d["output"]["comment"], material[vid][1]))]
    fig_failed = [{"variance_id": vid, "unmatched": d["figure_check"]["unmatched"]}
                  for vid, d in sorted(drafts.items()) if not d["figure_check"]["check_passed"]]
    return {
        "drafts": len(drafts),
        "drafts_per_model": dict(Counter(d["model"] for d in drafts.values()).most_common()),
        "planted_events_correct": sum(e["correct"] for e in events),
        "planted_events_total": sum(e["total"] for e in events),
        "planted_events": events,
        "noise_variances": len(noise),
        "noise_drafted": sum(vid in drafts for vid in noise),
        "noise_false_claims": len(false_claims),
        "noise_false_claims_for_review": false_claims,
        "noise_drafts_claiming_a_cause": len(claims),  # strict measure, kept for comparison
        "noise_claims_for_review": claims,
        "figure_check_passed": len(drafts) - len(fig_failed),
        "figure_check_failed": fig_failed,
        "sign_errors": len(signs),
        "sign_errors_for_review": signs,
        "within_60_words": sum(d["figure_check"]["word_count"] <= 60 for d in drafts.values()),
    }


versions = {"v1": load(AI / "v1" / "drafts.json"), "v2": load(AI / "drafts.json", "v2")}
result = {name: evaluate(d) if d else None for name, d in versions.items()}
(AI / "evaluation.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

# ---------------------------------------------------------------- print side by side
def cell(r, f):
    return "not run" if r is None else f(r)


rows = [
    ("Drafts", lambda r: f"{r['drafts']}/{len(material)}"),
    ("Models", lambda r: ", ".join(f"{m.removeprefix('gemini-')} {n}" for m, n in r["drafts_per_model"].items())),
    ("Planted events correct", lambda r: f"{r['planted_events_correct']}/{r['planted_events_total']}"),
    *[(f"  event {i} ({truth.expected_cause_category[i - 1]})",
       lambda r, i=i: f"{r['planted_events'][i - 1]['correct']}/{r['planted_events'][i - 1]['total']}")
      for i in range(1, len(truth) + 1)],
    ("Noise: false claims", lambda r: f"{r['noise_false_claims']}/{r['noise_drafted']}"),
    ("Noise: any cause (strict)", lambda r: f"{r['noise_drafts_claiming_a_cause']}/{r['noise_drafted']}"),
    ("Figure check passed", lambda r: f"{r['figure_check_passed']}/{r['drafts']}"),
    ("Sign errors", lambda r: f"{r['sign_errors']}/{r['drafts']}"),
    ("Within 60 words", lambda r: f"{r['within_60_words']}/{r['drafts']}"),
]
print(f"\n{'':32}{'v1':<46}{'v2':<46}")
for label, f in rows:
    print(f"{label:<32}{cell(result["v1"], f):<46}{cell(result["v2"], f):<46}")
for name, r in result.items():
    if r and r["noise_false_claims"]:
        print(f"\n{name} false claims on noise variances:")
        for c in r["noise_false_claims_for_review"]:
            print(f"  {c['variance_id']:<34}{'; '.join(c['reasons'])}")
for name, r in result.items():
    if r and r["sign_errors"]:
        print(f"\n{name} sign errors:")
        for s in r["sign_errors_for_review"]:
            print(f"  {s['variance_id']:<34}{s['error']}")
print("\nDetails (noise claims, figure check failures, sign errors) in data/ai/evaluation.json")
