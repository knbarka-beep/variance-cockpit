# Case sheet: Variance Cockpit

*All data is synthetic. The company and its customers and suppliers are fictional.*

## Problem

At month-end close a controller explains every large gap between budget and actual. Most of the time goes into finding the invoice or customer behind each gap. I wanted to see if AI could draft those comments in a way a controller can check.

## Approach

I generated two years of budget and ledger data for a fictional Danish manufacturer and planted six business events in it. All calculations are SQL views with reconciliation checks. Gemini drafts a comment for each material variance. A script with no AI checks every number in a draft against the input. The drafts are scored against the planted events, and the dashboard shows the result.

## Findings

- September 2026 closes with EBITDA of DKK 0,25m against a budget of DKK 1,55m. Lower revenue explains DKK 0,51m of the gap, mostly one customer buying less. Raw materials cost DKK 0,37m more than the budget flexed to volume. Temporary staff, overtime and one emergency repair invoice add the rest.
- My Excel reconciliation of the first data set showed marketing far over budget for a whole year from random noise alone. I fixed the generator so the monthly swings cancel out within each year.
- Versions 1 and 2 gave the model the following month. A controller at close cannot see that month, so those scores were too high. Version 3 removed it.
- The final version found the right cause in 12 of 15 planted event months.
- Claude suggested a review status for all 71 drafts. I checked a sample of 18 that was fixed before I looked, and agreed with 16. In one case Claude approved a draft that missed a supplier whose increase offset almost all of another supplier's drop.

## What I learned

A check is only fair if it is set before the result is known. The model's errors were rarely wrong numbers. They were plausible causes the ledger does not support, and look-ahead that made the scores look better than they were. A second model is a useful first reviewer, but I still found a miss it approved.

*Knut Barka*
