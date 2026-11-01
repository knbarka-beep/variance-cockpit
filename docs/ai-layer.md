# AI layer - Variance Cockpit

**All data is synthetic.** The company and all of its customers and suppliers are fictional.

For every material variance, Google's Gemini model drafts a short comment of the kind a controller would write. The controller then reviews each draft: approves it, edits it or rewrites it. The AI writes a first draft; a person decides what goes to management.

## The flow

```
build_db.py ──► data/variance.duckdb ──► draft_comments.py ──► data/ai/drafts.json
                                                           └─► data/ai/reviews.csv (controller fills in)
build_db.py (again) ──► data/export/comments.json (draft and final comment side by side)
evaluate_ai.py (reads the answer key) ──► data/ai/evaluation.json
```

| Script | Does |
|---|---|
| `scripts/draft_comments.py` | Builds the input for each material variance from the database, calls Gemini for new or changed inputs, and runs the figure check |
| `scripts/evaluate_ai.py` | Compares the drafts with the planted events. **The only script that reads `data/truth/`** |
| `prompts/variance_comment.md` | The instructions given to the model (system prompt) |
| `config/settings.yaml` → `ai:` | Model fallback list, temperature, call limits, company context |

## What goes in

One JSON document per material variance, built only from the DuckDB views:

- **Company context:** one line from the config.
- **The variance:** period, account, cost centre, variance type (`total` vs budget, or `price` vs flexed budget), actual, budget (and flexed budget for price rows), variance in DKK and %, and whether it is favourable.
- **For raw materials and packaging:** the price/volume split.
- **The ledger lines behind the variance:** date, counterparty, description and amount, largest first. At most 40 lines are shown; the rest are summarised as a count and a total.
- **For revenue variances (from v2):** revenue per customer this month vs that customer's average for the previous 3 months, in amount and %, largest change first. It comes from the SQL view `v_customer_month`. It shows whether one customer explains the variance. The 3-month average is not seasonally adjusted.
- **For cost variances (from v2):** the largest ledger line is marked, with its size as a percentage of the variance (`largest_line_share_of_variance_pct`).
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
- **Noise variances** (material, but no planted event behind them): how many drafts claim a specific cause anyway? These are possible hallucinations, listed for review. Some may be fair readings of the ledger lines; that is for the controller to judge.
- **Figure check pass rate** and the 60-word limit.
- **Sign errors:** an amount written with a minus sign, or "favourable" and "unfavourable" used the wrong way round.

The evaluation compares versions side by side and writes both to `data/ai/evaluation.json`.

## Versions

| | v1 (baseline) | v2 |
|---|---|---|
| Prompt | `prompts/v1/variance_comment.md` | `prompts/variance_comment.md` |
| Drafts | `data/ai/v1/drafts.json` (kept as the baseline) | `data/ai/drafts.json`, each with `prompt_version: v2` |
| Model | Fallback across 3.8 Flash, 3.6 Flash and 3.5 Flash-Lite as quotas ran out | `gemini-3.5-flash-lite` only, so all drafts are comparable |
| Input | Ledger lines, previous 3 months, following month, price/volume split | Same, plus the customer table for revenue and the marked largest line for costs |

v2 prompt changes:
- Name a specific cause only if one ledger line, one counterparty or one customer explains about half of the variance. Otherwise say "unclear" and what to check.
- Use "persistent" or "price" only if the previous months show the same direction and size.
- Write amounts as positive numbers, and use the words favourable and unfavourable for direction.
- Never calculate new totals or differences.

v1 results (71 drafts): 10/15 planted-event variances correct, 30/55 noise drafts claiming a cause, 69/71 figure check passed, 12/71 sign errors.

## Known limits

- **Synthetic data with planted causes.** The evaluation shows that the model reads the data correctly when the cause is visible in the ledger lines. It does **not** show that it would find causes in a real company, where causes are often outside the ledger (a phone call, a contract, a decision).
- **Small sample:** six planted events and about 70 variances.
- **Fixed categories:** the cause categories are a simplification. A real variance can have several causes.
- **The figure check checks numbers, not meaning.** It catches an invented amount, but not a correct amount attached to the wrong explanation.
- **Hindsight:** the following month is given as context. In a real month-end close it would not exist yet.
- **Model changes:** a different model can give different drafts, and with the fallback list one run can mix models. The model name is stored with each draft, so differences can be traced. Changing the model list does not redraft existing drafts; delete `data/ai/drafts.json` to start again.
