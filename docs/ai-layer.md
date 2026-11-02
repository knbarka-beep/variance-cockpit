# AI layer - Variance Cockpit

**All data is synthetic.** The company and all of its customers and suppliers are fictional.

For every material variance, Google's Gemini model drafts a short comment of the kind a controller would write. The controller then reviews each draft: approves it, edits it or rewrites it. The AI writes a first draft; a person decides what goes to management.

## The flow

```
build_db.py ──► data/variance.duckdb ──► draft_comments.py ──► data/ai/drafts.json
                                                           └─► data/ai/reviews.csv (one empty row per variance)
review_export.py ──► data/check/review.xlsx (controller fills in) ──► review_import.py ──► data/ai/reviews.csv
build_db.py (again) ──► data/export/comments.json (draft and final comment side by side)
evaluate_ai.py (reads the answer key) ──► data/ai/evaluation.json
```

| Script | Does |
|---|---|
| `scripts/draft_comments.py` | Builds the input for each material variance from the database, calls Gemini for new or changed inputs, and runs the figure check |
| `scripts/evaluate_ai.py` | Compares the drafts with the planted events. **The only script that reads `data/truth/`** |
| `scripts/review_export.py` | Writes the review workbook `data/check/review.xlsx` |
| `scripts/review_import.py` | Checks the workbook and writes the review columns back to `data/ai/reviews.csv` |
| `prompts/variance_comment.md` | The instructions given to the model (system prompt) |
| `config/settings.yaml` → `ai:` | Model fallback list, temperature, call limits, company context |

## What goes in

One JSON document per material variance, built only from the DuckDB views:

- **Company context:** one line from the config.
- **The variance:** period, account, cost centre, variance type (`total` vs budget, or `price` vs flexed budget), actual, budget (and flexed budget for price rows), variance in DKK and %, and whether it is favourable.
- **For raw materials and packaging:** the price/volume split.
- **The ledger lines behind the variance:** date, counterparty, description and amount, largest first. At most 40 lines are shown; the rest are summarised as a count and a total.
- **For revenue variances (from v2):** revenue per customer this month vs that customer's average for the previous 3 months, in amount and %, largest change first. It comes from the SQL view `v_customer_month`. It shows whether one customer explains the variance. The 3-month average is not seasonally adjusted.
- **For cost variances except raw materials and packaging (from v2):** cost per supplier this month vs that supplier's average for the previous 3 months on the same account and cost centre, with the number of lines. It comes from the SQL view `v_counterparty_month`. Lines without a counterparty (payroll, card payments, expense claims) are grouped as "(no counterparty)". The largest ledger line is also marked, for information only.
- **For each customer or supplier (from v2):** its change as a share of the variance (`change_share_of_variance_pct`). Positive means it moves in the same direction as the variance.
- **The same account and cost centre for the previous 3 months:** so the model can tell a one-off from a persistent change.
- **The following month, if available:** so a reversal or correction is visible. This is given for every variance, not only for energy: the script must not know which variances are planted events.

Run `draft_comments.py --show 2026-07_4020_Production` to see the exact input for one variance.

## What comes out

Gemini must return JSON in a fixed structure. The API enforces it, so the answer cannot be free text:

| Field | Meaning |
|---|---|
| `comment` | The draft comment, at most 60 words, British English, European number format |
| `cause_category` | `price`, `volume`, `one_off`, `timing`, `staffing` or `unclear` |
| `persistence` | `one_off`, `timing`, `persistent` or `unknown` |
| `figures_cited` | The numbers the model says it used |
| `no_clear_cause` | `true` if the data does not show a clear cause |

Each entry in `data/ai/drafts.json` also stores the variance_id, a hash of the input, the model name, a timestamp and the figure check result.

`data/ai/reviews.csv` has one row per variance with three empty columns for the controller: `status`, `final_comment` and `reviewer_note`. A rerun adds rows for new variances but never changes rows that are already there.

## The controller's review

Reviewing 71 comments in a CSV file is awkward, so the review happens in Excel:

1. `review_export.py` writes `data/check/review.xlsx`, in the same row order as `reviews.csv`. Each row shows the variance (period, account, cost centre, amount, %), the AI comment, its cause category and persistence, then the three review columns: `status`, `final_comment`, `reviewer_note`. The status column has a drop-down (approved, edited, rejected), the comment columns wrap their text, and the top row is frozen. Review work already in `reviews.csv` is shown again. The script will not overwrite a workbook that holds work not yet imported.
2. The controller fills in the review columns.
3. `review_import.py` writes only `variance_id`, `status`, `final_comment` and `reviewer_note` back to `reviews.csv`. It stops with an error, and changes nothing, if a status is anything other than empty, approved, edited or rejected, if a row marked edited has no final comment, or if a variance_id is missing.
4. `build_db.py` runs the same status checks on `reviews.csv` before it builds anything, so a hand-edited CSV with a bad status cannot reach the dashboard.

`scripts/test_review.py` tests the status rules. The workbook lives in `data/check/`, which is not committed; `reviews.csv` is the record that is committed.

## The figure check (no AI)

Language models can make up numbers. So every number in a comment is checked against the input by ordinary code, with no AI involved:

1. Find every number in the comment, in European format: `DKK 236.321`, `DKK 0,24m`, `236k`, `8,9 %`.
2. Collect every number in the input, including numbers inside text such as invoice numbers and years.
3. A figure passes if it matches an input number:
   - **Amounts:** within 1 %, or within the rounding shown (`DKK 0,24m` may be anything from 235.000 to 245.000).
   - **Percentages:** within 0,1 point, or within the rounding shown (`9 %` may be 8,5 to 9,5).
4. The draft passes if every figure matches. Any figure that doesn't match is listed for the controller to check.

Bare small numbers without `DKK` or a unit (like "3 months" or "line 2") are skipped. So are numbers written as words. A number in English format (`236,321`) is read the European way and will usually fail, which is intended: it breaks the formatting rule.

`scripts/test_draft_comments.py` tests the parser and the matching, plus the retry and model-fallback logic with a fake client (no API calls).

## Cost and rate control

- **Cache:** each draft stores a hash of its input and the prompt. A rerun only calls the API for drafts that are missing or whose input or prompt changed. An unchanged data set costs zero calls. The model is deliberately not part of the hash, so a draft made by a fallback model stays cached.
- **`max_calls_per_run`** (default 100): a hard cap per run.
- **`seconds_between_calls`** (default 7): about 8 calls a minute, inside the free-tier rate limit.
- **Temporary errors:** a per-minute rate limit (429), a server error or busy server (500, 502, 503, 504), or a call with no answer within 60 seconds means wait and retry the same model, up to 4 times. If the API says how long to wait, the script waits that long; otherwise 10, 20, 40 and 80 seconds.
- **Model fallback:** `models` in the config is a list tried in order: `gemini-3.8-flash`, `gemini-3.7-flash`, `gemini-3.6-flash`, `gemini-3.5-flash`, `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`. (The 2.5 models are listed by the API but returned "not found" for this key on the free tier.) A model is skipped for the rest of the run, with the reason logged, if its free-tier quota is used up ("limit: 0" or a daily limit), if it doesn't exist for this key, or if a call still fails after 4 retries (for example, it keeps timing out). The next model in the list is then used. If every model is used up, the run stops cleanly, saves what is done and prints how many drafts are still missing. A rerun the next day continues from there.
- **Drafts may come from different models.** When the free tier runs out halfway, later drafts are written by a fallback model. Each draft stores the model that actually wrote it, and the evaluation counts drafts per model.
- **`--dry-run`:** shows how many calls a run would make, without a key and without calling the API.
- **On the free tier the calls cost nothing.** If billing is enabled on the Google Cloud project behind the key, the calls are charged. A full run of about 70 short calls on a Flash model costs a few cents at most.

## Why the dashboard does not call the API live

- **Reproducible:** the same variance always shows the same draft. Live calls can give a different answer every time.
- **Reviewable:** a comment must be reviewed before it reaches management. A text that changes on every page load can't be reviewed.
- **Cost and speed:** each draft is paid for once, not on every page view, and the dashboard loads instantly.
- **Secure:** the API key never goes near the dashboard. A static site cannot keep a key secret.
- **Auditable:** each draft has its input hash, model and timestamp, so you can always tell what the AI saw.

## Safeguards

- **The answer key is blocked.** `draft_comments.py` installs a Python audit hook that raises an error if anything in the process tries to open a file in `data/truth/`. Only `evaluate_ai.py` reads the answer key.
- **The key is never printed.** It is read from `.env` with python-dotenv. `.env` is in `.gitignore`.
- **The model may only use facts in the input.** When the data does not show a cause, it must say so and suggest what to check.

## Evaluation

`evaluate_ai.py` is a first automatic pass. The controller judges the comments themselves.

- **Planted events:** does the draft for each event name the expected cause category? Event 6 (scattered small purchases) must also be flagged `no_clear_cause = true`.
- **Noise variances** (material, but no planted event behind them), two measures:
  - **False claims** (main measure): the draft says `price` or `persistent`, or it names a counterparty or invoice number that is not behind the variance. Naming the supplier or invoice that really drives it, as one-off or timing, is a correct reading of the ledger and does not count.
  - **Any cause (strict):** any category other than `unclear`. Kept for comparison.
- **Figure check pass rate** and the 60-word limit.
- **Sign errors:** an amount written with a minus sign, or "favourable" and "unfavourable" used the wrong way round.

The evaluation compares versions side by side and writes both to `data/ai/evaluation.json`.

## Versions

| | v1 (baseline) | v2 |
|---|---|---|
| Prompt | `prompts/v1/variance_comment.md` | `prompts/variance_comment.md` |
| Drafts | `data/ai/v1/drafts.json` (kept as the baseline) | `data/ai/drafts.json`, each with `prompt_version: v2` |
| Model | Fallback across 3.8 Flash, 3.6 Flash and 3.5 Flash-Lite as quotas ran out | `gemini-3.5-flash-lite` only, so all drafts are comparable |
| Input | Ledger lines, previous 3 months, following month, price/volume split | Same, plus the customer table for revenue and the supplier table for costs |

v2 prompt changes:
- Name a specific cause only if one supplier (costs) or one customer (revenue) explains about half of the variance or more, measured as its change against its own 3-month average. "(no counterparty)" counts only as a single line (such as one payroll line), not as many small card payments. Otherwise say "unclear" and what to check.
- Use "persistent" only if the previous months show the same direction and size. A `price` row may be called "price" from the first month, because the flexed budget already removes volume.
- Raw materials and packaging are explained by the price/volume split, not by suppliers. Their supplier mix varies at random in this data, so they get no supplier table. Price rows get previous and following months on the same flexed basis, plus a short note.
- Write amounts as positive numbers, and use the words favourable and unfavourable for direction.
- Never calculate new totals or differences.

| Result (71 drafts) | v1 | v2 |
|---|---|---|
| Planted-event variances correct | 10/15 | 13/15 |
| Noise: false claims | 9/55 | 5/55 |
| Noise: any cause (strict) | 30/55 | 40/55 |
| Figure check passed | 69/71 | 71/71 |
| Sign errors | 12/71 | 0/71 |

v2 was written after the v1 errors were known, so its score is measured on the same events the prompt was tuned against (see the README). The strict noise measure rose because v2 names the real invoice behind a noise variance more often, as one-off or timing; under the false-claim measure that is a correct reading.

## Known limits

- **Noise is a real invoice in the ledger.** In this data, a noise variance on a lumpy account (repairs, marketing, IT) comes from an invoice that really is unusually large or small that month. No baseline can tell it apart from a genuine one-off, so a draft that names that invoice is reading the ledger correctly. Claiming "price" or "persistent" for it would be a real error.
- **Synthetic data with planted causes.** The evaluation shows that the model reads the data correctly when the cause is visible in the ledger lines. It does **not** show that it would find causes in a real company, where causes are often outside the ledger (a phone call, a contract, a decision).
- **Small sample:** six planted events and about 70 variances.
- **Fixed categories:** the cause categories are a simplification. A real variance can have several causes.
- **The figure check checks numbers, not meaning.** It catches an invented amount, but not a correct amount attached to the wrong explanation.
- **Hindsight:** the following month is given as context. In a real month-end close it would not exist yet.
- **Model changes:** a different model can give different drafts, and with the fallback list one run can mix models. The model name is stored with each draft, so differences can be traced. Changing the model list does not redraft existing drafts; delete `data/ai/drafts.json` to start again.
