"""Draft a variance comment for every material variance with Gemini.

The AI text is generated once and stored in data/ai/drafts.json; the dashboard never calls the API.

Usage (from the project folder):
  .venv/Scripts/python scripts/draft_comments.py --list-models   # available Flash models (needs key, free)
  .venv/Scripts/python scripts/draft_comments.py --dry-run       # build inputs, count calls; no key, no API
  .venv/Scripts/python scripts/draft_comments.py --show ID       # print the input for one variance_id
  .venv/Scripts/python scripts/draft_comments.py                 # call the API for new or changed inputs only

Needs data/variance.duckdb (run build_db.py first). Run build_db.py again afterwards to export the drafts.
Never reads data/truth/: an audit hook makes any attempt fail.
"""
import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Literal

import duckdb
import yaml
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[1]
TRUTH = os.path.normcase(str(ROOT / "data" / "truth"))


def _block_answer_key(event, args):
    """Audit hook: refuse any file access inside data/truth/ from this process."""
    if event in ("open", "os.listdir", "os.scandir") and args and isinstance(args[0], (str, bytes, os.PathLike)):
        path = os.path.normcase(os.path.abspath(os.fsdecode(args[0])))
        if path == TRUTH or path.startswith(TRUTH + os.sep):
            raise AssertionError(f"draft_comments.py must never read the answer key: {path}")


sys.addaudithook(_block_answer_key)

cfg = yaml.safe_load((ROOT / "config" / "settings.yaml").read_text(encoding="utf-8"))
ai = cfg["ai"]
PROMPT = (ROOT / "prompts" / "variance_comment.md").read_text(encoding="utf-8")  # current version; old ones in prompts/v1/ ...
AI_DIR = ROOT / "data" / "ai"
DRAFTS = AI_DIR / "drafts.json"
REVIEWS = AI_DIR / "reviews.csv"


class Draft(BaseModel):
    """The JSON structure Gemini must return (enforced by the API)."""
    comment: str
    cause_category: Literal["price", "volume", "one_off", "timing", "staffing", "unclear"]
    persistence: Literal["one_off", "timing", "persistent", "unknown"]
    figures_cited: list[float]
    no_clear_cause: bool


# ---------------------------------------------------------------- input per variance
def plain(v):
    if isinstance(v, Decimal):
        return round(float(v), 2)
    return v


def rows(con, sql, params=()):
    cur = con.execute(sql, params)
    cols = [d[0] for d in cur.description]
    return [{c: plain(v) for c, v in zip(cols, r)} for r in cur.fetchall()]


def month_rows(con, v, offsets):
    """Actual and budget for the same account and cost centre, N months before/after."""
    return rows(con, f"""
        SELECT period, actual_dkk, budget_dkk, variance_profit_dkk AS variance_dkk
        FROM v_account_month
        WHERE account_no = ? AND cost_centre = ?
          AND period_date IN ({", ".join("CAST(? AS DATE) + to_months(?)" for _ in offsets)})
        ORDER BY period""",
        [v["account_no"], v["cost_centre"]] + [x for o in offsets for x in (v["period"] + "-01", o)])


def build_input(con, v):
    is_price = v["variance_type"] == "price"
    inp = {
        "company": ai["company_context"],
        "period": v["period"],
        "account": f"{v['account_no']} {v['account_name']}",
        "pl_group": v["pl_group"],
        "cost_centre": v["cost_centre"],
        "variance_type": v["variance_type"],
        "compared_with": "flexed budget" if is_price else "budget",
        "actual_dkk": v["actual_dkk"],
        "budget_dkk": v["budget_dkk"],
    }
    if is_price:
        inp["flexed_budget_dkk"] = v["flexed_budget_dkk"]
    inp |= {"variance_dkk": v["variance_profit_dkk"], "variance_pct": v["variance_pct"],
            "favourable": v["favourable"]}

    if v["pl_group"] == "Cost of materials":
        split = rows(con, """
            SELECT volume_pct_of_budget, budget_dkk, flexed_budget_dkk, actual_dkk,
                   volume_variance_profit_dkk AS volume_variance_dkk,
                   price_usage_variance_profit_dkk AS price_usage_variance_dkk,
                   price_usage_variance_pct, total_variance_profit_dkk AS total_variance_dkk
            FROM v_flexed_budget WHERE period = ? AND account_no = ? AND cost_centre = ?""",
            [v["period"], v["account_no"], v["cost_centre"]])
        inp["price_volume_split"] = split[0]

    lines = rows(con, """
        SELECT posting_date AS date, counterparty, description, amount_dkk
        FROM v_transactions WHERE cell_id = ?
        ORDER BY ABS(amount_dkk) DESC, line_id""", [v["cell_id"]])
    for line in lines:
        line["date"] = str(line["date"])

    # Which customer or supplier explains the variance? Each one's change vs its own average
    # of the 3 months before, and that change as a share of the variance.
    # Share sign: positive = the change moves in the same direction as the variance.
    # (Revenue: more revenue = higher profit. Costs: more cost = lower profit, hence the minus.)
    keys = [v["period"], v["account_no"], v["cost_centre"]]
    profit_direction = 1 if v["pl_group"] == "Revenue" else -1
    if v["pl_group"] == "Revenue":
        table = rows(con, """
            SELECT customer, revenue_dkk, avg_prev_3_months_dkk, change_dkk, change_pct
            FROM v_customer_month WHERE period = ? AND account_no = ? AND cost_centre = ?
            ORDER BY ABS(change_dkk) DESC NULLS LAST, customer""", keys)
        inp["revenue_by_customer"] = table
    else:
        table = rows(con, """
            SELECT counterparty AS supplier, cost_dkk, avg_prev_3_months_dkk, change_dkk, change_pct,
                   lines, avg_lines_prev_3_months
            FROM v_counterparty_month WHERE period = ? AND account_no = ? AND cost_centre = ?
              AND (cost_dkk <> 0 OR avg_prev_3_months_dkk <> 0)
            ORDER BY ABS(change_dkk) DESC NULLS LAST, counterparty""", keys)
        inp["cost_by_supplier"] = table
        if lines:  # for information only; not used by the cause rule
            lines[0]["largest_line"] = True
            inp["largest_line_share_of_variance_pct"] = round(
                100 * abs(lines[0]["amount_dkk"]) / abs(v["variance_profit_dkk"]), 1)
    for row in table:
        if row["change_dkk"] is not None:
            row["change_share_of_variance_pct"] = round(
                100 * profit_direction * row["change_dkk"] / v["variance_profit_dkk"], 1)

    n = ai["max_ledger_lines"]
    inp["ledger_lines"] = lines[:n]
    if len(lines) > n:
        inp["ledger_lines_not_shown"] = {"count": len(lines) - n,
                                         "total_dkk": round(sum(x["amount_dkk"] for x in lines[n:]), 2)}

    inp["previous_months"] = month_rows(con, v, [-3, -2, -1])
    following = month_rows(con, v, [1])
    if following:  # shows a later reversal or a continuing trend
        inp["following_month"] = following[0]
    return inp


def input_hash(inp):
    """Hash of the prompt and the input. The model is left out on purpose: a draft made by a
    fallback model stays cached, so a rerun only does the drafts that are still missing."""
    blob = json.dumps({"prompt": PROMPT, "input": inp}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------- figure check (no AI)
FIGURE = re.compile(
    r"(?P<dkk>DKK\s*)?[-−–]?\s*(?P<num>\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?)"
    r"\s*(?P<unit>%|million\b|mio\b|bn\b|m\b|k\b)?", re.IGNORECASE)
SCALE = {"million": 1e6, "mio": 1e6, "m": 1e6, "k": 1e3, "bn": 1e9}


def parse_figures(text):
    """Find the numbers in a comment written in European format.
    'DKK 236.321' -> 236321, 'DKK 0,24m' -> 240000, '8,9 %' -> 8.9 (pct), '236k' -> 236000.
    Bare numbers under 100 without DKK or a unit (e.g. '3 months', 'line 2') are skipped."""
    found = []
    for m in FIGURE.finditer(text):
        whole, _, decimals = m["num"].replace(".", "").partition(",")
        unit = (m["unit"] or "").lower()
        value = float(whole + ("." + decimals if decimals else ""))
        if not m["dkk"] and not unit and value < 100:
            continue
        scale = SCALE.get(unit, 1)
        found.append({"text": m.group(0).strip(), "value": value * scale,
                      "kind": "pct" if unit == "%" else "amount",
                      "precision": 0.5 * 10 ** -len(decimals) * scale})  # the rounding shown
    return found


def input_numbers(obj):
    """Every number in the input, including numbers inside text (invoice numbers, years)."""
    if isinstance(obj, bool) or obj is None:
        return []
    if isinstance(obj, (int, float)):
        return [abs(float(obj))]
    if isinstance(obj, str):
        return [float(x) for x in re.findall(r"\d+", obj)]
    items = obj.values() if isinstance(obj, dict) else obj
    return [n for item in items for n in input_numbers(item)]


def figure_check(comment, inp):
    """Each figure must match an input number: amounts within 1 % or the rounding shown,
    percentages within 0.1 point or the rounding shown."""
    candidates = input_numbers(inp)
    figures = parse_figures(comment)
    unmatched = []
    for f in figures:
        tol = max(0.1 if f["kind"] == "pct" else 0.01 * f["value"], f["precision"])
        if not any(abs(f["value"] - c) <= tol for c in candidates):
            unmatched.append(f["text"])
    return {"figures_found": len(figures), "figures_matched": len(figures) - len(unmatched),
            "unmatched": unmatched, "check_passed": not unmatched,
            "word_count": len(comment.split())}


# ---------------------------------------------------------------- Gemini
def client():
    from dotenv import load_dotenv
    from google import genai
    load_dotenv(ROOT / ".env")
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        sys.exit("GEMINI_API_KEY is empty. Paste your key into .env (GEMINI_API_KEY=...).")
    # 60 s timeout per call; the SDK's own retries are switched off so call_gemini's retry
    # logic is the only one (one place, predictable waiting times).
    return genai.Client(api_key=key, http_options=genai.types.HttpOptions(
        timeout=CALL_TIMEOUT_S * 1000, retry_options=genai.types.HttpRetryOptions(attempts=1)))


def list_models():
    gemini = client()  # keep a reference: a temporary client is closed before the list is fetched
    for m in gemini.models.list():
        if "flash" in m.name and "generateContent" in (m.supported_actions or []):
            print(f"{m.name:<45} {m.display_name}")


class ModelUnavailable(Exception):
    """This model cannot be used for the rest of the run (quota used up or not available)."""


MAX_RETRIES = 4
CALL_TIMEOUT_S = 60


def call_gemini(gemini, model, inp):
    """One draft from one model.
    - Quota used up ('limit: 0' or a daily limit) or model not found -> ModelUnavailable.
    - Per-minute rate limit (429), server error or busy (500, 502, 503, 504), timeout (60 s)
      or a network error -> wait and retry the same model: the delay the API asks for,
      otherwise 10, 20, 40, 80 seconds (max 4 retries). Still failing after 4 retries
      -> ModelUnavailable, so the run falls back to the next model."""
    import httpx
    from google.genai import errors, types
    config = types.GenerateContentConfig(
        system_instruction=PROMPT, temperature=ai["temperature"],
        response_mime_type="application/json", response_schema=Draft)
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = gemini.models.generate_content(
                model=model, contents=json.dumps(inp, ensure_ascii=False, indent=1), config=config)
            return resp.parsed or Draft.model_validate_json(resp.text)
        except (errors.APIError, httpx.TransportError) as e:
            if isinstance(e, httpx.TransportError):  # timeout or network problem: temporary
                code, text = type(e).__name__, ""
            else:
                code, text = e.code, f"{e} {e.details}"
                if code == 404 or (code == 429 and re.search(r"limit: 0\b|PerDay", text)):
                    reason = "not found" if code == 404 else "free-tier quota used up"
                    api_says = (e.message or "").split("\n")[0][:160]  # Google's own explanation, shortened
                    raise ModelUnavailable(f"{model}: {reason} ({code}: {api_says})") from None
                if code not in (429, 500, 502, 503, 504):
                    raise
            if attempt == MAX_RETRIES:
                raise ModelUnavailable(f"{model}: still failing after {MAX_RETRIES} retries ({code})") from None
            asked = re.search(r"retryDelay\W+(\d+(?:\.\d+)?)s", text)
            wait = float(asked[1]) + 1 if asked else 10 * 2 ** attempt
            print(f"   {model}: {code}, waiting {wait:.0f}s (retry {attempt + 1}/{MAX_RETRIES})", flush=True)
            time.sleep(wait)


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list-models", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--show", metavar="VARIANCE_ID")
    args = ap.parse_args()
    if args.list_models:
        return list_models()

    con = duckdb.connect(str(ROOT / "data" / "variance.duckdb"), read_only=True)
    variances = rows(con, "SELECT * FROM v_material_variances ORDER BY period, rank_in_month")
    inputs = {v["variance_id"]: build_input(con, v) for v in variances}
    con.close()
    if args.show:
        return print(json.dumps(inputs[args.show], indent=2, ensure_ascii=False))

    old = {d["variance_id"]: d for d in json.loads(DRAFTS.read_text(encoding="utf-8"))} if DRAFTS.exists() else {}
    hashes = {vid: input_hash(inp) for vid, inp in inputs.items()}
    todo = [vid for vid in inputs if old.get(vid, {}).get("input_hash") != hashes[vid]]
    n_calls = min(len(todo), ai["max_calls_per_run"])
    print(f"{len(inputs)} material variances, {len(inputs) - len(todo)} cached, {len(todo)} new or changed.")
    print(f"This run: up to {n_calls} API calls, models in order: {', '.join(ai['models'])} "
          f"(about {n_calls * ai['seconds_between_calls'] // 60 + 1} min).")
    if args.dry_run:
        return print("Dry run: no API calls made, nothing written.")

    import httpx
    from google.genai import errors
    gemini = client() if n_calls else None
    available = list(ai["models"])  # models still usable in this run
    drafts = {vid: old[vid] for vid in inputs if vid in old}
    save(drafts, inputs)
    try:
        for i, vid in enumerate(todo[:n_calls], 1):
            started = time.monotonic()
            draft = None
            while available and draft is None:
                try:
                    draft = call_gemini(gemini, available[0], inputs[vid])
                except ModelUnavailable as e:
                    print(f"   {e} -> skipping this model for the rest of the run", flush=True)
                    available.pop(0)
            if draft is None:
                print("Every model in the list is unavailable. Stopping.")
                break
            drafts[vid] = {"variance_id": vid, "input_hash": hashes[vid], "model": available[0],
                           "prompt_version": ai["prompt_version"],
                           "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                           "output": draft.model_dump()}
            save(drafts, inputs)  # after every draft, so progress is never lost
            print(f"[{len(drafts)}/{len(inputs)}] {vid:<34} {available[0]:<22} "
                  f"{time.monotonic() - started:5.1f}s", flush=True)
            if i < n_calls:
                time.sleep(ai["seconds_between_calls"])
    except (errors.APIError, httpx.TransportError) as e:  # anything retries could not fix
        print(f"Stopped: {type(e).__name__} {getattr(e, 'code', '')}.")
    finally:
        save(drafts, inputs)
        print(f"Saved {len(drafts)} drafts to {DRAFTS.relative_to(ROOT)}. "
              f"{len(inputs) - len(drafts)} still missing; rerun to continue.")


def save(drafts, inputs):
    """Write drafts.json (with a fresh figure check) and reviews.csv.
    Written to a temporary file first, so an interrupted save never leaves a broken file."""
    for vid, d in drafts.items():  # the figure check is cheap, so always redo it
        d["figure_check"] = figure_check(d["output"]["comment"], inputs[vid])
    AI_DIR.mkdir(parents=True, exist_ok=True)
    ordered = [drafts[vid] for vid in inputs if vid in drafts]
    tmp = DRAFTS.with_suffix(".tmp")
    tmp.write_text(json.dumps(ordered, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, DRAFTS)
    write_reviews(list(inputs))


def write_reviews(variance_ids):
    """One row per variance_id. Rows that already exist are kept exactly as they are."""
    cols = ["variance_id", "status", "final_comment", "reviewer_note"]
    existing = []
    if REVIEWS.exists():
        with REVIEWS.open(encoding="utf-8", newline="") as f:
            existing = list(csv.DictReader(f))
    known = {r["variance_id"] for r in existing}
    new = [{"variance_id": vid, "status": "", "final_comment": "", "reviewer_note": ""}
           for vid in variance_ids if vid not in known]
    with REVIEWS.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(existing + new)


if __name__ == "__main__":
    main()
