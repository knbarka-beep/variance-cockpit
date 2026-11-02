# Variance Cockpit

A budget vs actual cockpit for month-end close: SQL views calculate the variances, AI drafts a comment for each material one, and a controller reviews the drafts. It is a portfolio project for roles in controlling and finance transformation, so a hiring manager should understand it in two minutes. Clarity beats cleverness.

Write code, docs and commits in English. **Always answer the user in Norwegian bokmål.**

## Who you work with

The user builds finance tools with AI and is not a developer. Explain each choice in a sentence or two, in words they can repeat in a job interview. If a solution is too technical for them to explain, pick the simpler one, even if it is less elegant.

## Fixed rules (absolute)

These protect the credibility of the project. If a task seems to need breaking one, stop and ask.

- **The answer key (`data/truth/`) is read only for evaluation.** `evaluate_ai.py` scores the AI against it; `generate_data.py` writes it and `check_data.py` checks that the planted events exist in the data. Nothing that feeds the AI or the dashboard may read it, or the evaluation proves nothing.
- **The AI never sees data from months after the month it comments on.** At month-end close the future does not exist; look-ahead makes the scores look better than reality.
- **All data is synthetic and labelled as such.** No real company names, logos or designs. A reader must never mistake it for real data.
- **No claim in the README, docs or dashboard that the numbers do not support.** Limitations are stated openly. An honest weak result is worth more than an inflated one.
- **Evaluation rules never change after the result has been seen.** Otherwise the measure is tuned to the answer.
- **Nothing from the author's employer:** no data, routines, thresholds or systems. The project must be clearly the user's own work.

## Ask first

Ask before you:
- call the Gemini API beyond a single test call, or do anything that costs money;
- change what is measured or how it is measured;
- delete data;
- change `data/ai/reviews.csv` or `data/check/review.xlsx` (the controller's work).

## Just do it

No need to ask for small technical choices, debugging, tests, refactoring that does not change any numbers, commits with clear messages, and a push when a step is done and the tests pass. Mention what you chose in a line.

## Before saying something is done

Run the tests (`scripts/test_draft_comments.py`, `scripts/test_review.py`) and the reconciliation checks (`scripts/build_db.py` stops if any check in `v_checks` fails). Say briefly what you checked and what the result was. If something was skipped, say so.

## Where the details are

- `docs/ai-layer.md`: AI input and output, the figure check, cost control, evaluation, versions.
- `docs/sql-guide.md`: the SQL views and reconciliation checks.
- `docs/data-spec.md`: the synthetic data and the planted events.
- `config/settings.yaml`: every assumption in one place.

Read these rather than guessing, and update them when behaviour changes. Do not copy their content here.
