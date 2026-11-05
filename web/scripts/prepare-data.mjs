// Copies the fields the dashboard needs from ../data/export into lib/dashboard.json.
// AI quality: only the aggregate scores for the drafts shown, never which variances are planted events.
import { readFileSync, writeFileSync } from "node:fs";

const load = (p) => JSON.parse(readFileSync(new URL(`../../data/${p}`, import.meta.url), "utf8"));
const pick = (o, keys) => Object.fromEntries(keys.map((k) => [k, o[k]]));

const meta = load("export/meta.json");
const comments = Object.fromEntries(load("export/comments.json").map((c) => [c.variance_id, c]));
const versions = [...new Set(Object.values(comments).map((c) => c.ai_prompt_version).filter(Boolean))];
const evaluation = load("ai/evaluation.json");
const ev = versions.length === 1 ? evaluation[versions[0]] : null;

const data = {
  meta: pick(meta, ["company_name", "notice", "periods", "latest_period", "materiality"]),
  kpis: load("export/kpis.json").filter((r) => r.basis === "month").map((r) => pick(r, [
    "period", "revenue_actual_dkk", "revenue_budget_dkk", "revenue_variance_dkk", "revenue_variance_pct",
    "ebitda_actual_dkk", "ebitda_budget_dkk", "ebitda_variance_dkk", "ebitda_variance_pct",
    "ebitda_margin_actual_pct", "ebitda_margin_budget_pct"])),
  bridge: load("export/bridge.json").filter((r) => r.basis === "month").map((r) => pick(r, [
    "period", "step_no", "step", "step_type", "amount_dkk", "bar_start_dkk", "bar_end_dkk"])),
  accountMonth: load("export/account_month.json").map((r) => pick(r, [
    "period", "account_no", "account_name", "pl_group", "cost_centre", "actual_dkk", "budget_dkk", "variance_profit_dkk"])),
  monthSummaries: Object.fromEntries(load("export/month_summaries.json").map((r) => [r.period, r.summary])),
  flexed: load("export/flexed_materials.json").map((r) => pick(r, [
    "period", "account_no", "account_name", "actual_dkk", "flexed_budget_dkk", "volume_pct_of_budget", "total_variance_profit_dkk",
    "price_usage_variance_profit_dkk", "volume_variance_profit_dkk"])),
  transactions: load("export/transactions.json").map((r) => pick(r, [
    "cell_id", "posting_date", "counterparty", "description", "amount_dkk"])),
  variances: load("export/material_variances.json").map((v) => ({
    ...pick(v, ["variance_id", "variance_type", "cell_id", "period", "rank_in_month", "account_no",
      "account_name", "pl_group", "cost_centre", "actual_dkk", "budget_dkk", "flexed_budget_dkk",
      "variance_profit_dkk", "variance_pct", "favourable"]),
    ...pick(comments[v.variance_id] ?? {}, ["ai_comment", "ai_cause_category", "ai_persistence",
      "figure_check_passed", "ai_model", "ai_prompt_version", "review_status", "final_comment", "reviewer_note", "reviewed_by"]),
  })),
  aiQuality: ev && {
    version: versions[0],
    models: Object.keys(ev.drafts_per_model),
    drafts: ev.drafts,
    figure_check_passed: ev.figure_check_passed,
    planted_correct: ev.planted_events_correct,
    planted_total: ev.planted_events_total,
    noise_false_claims: ev.noise_false_claims,
    noise_drafted: ev.noise_drafted,
  },
};
writeFileSync(new URL("../lib/dashboard.json", import.meta.url), JSON.stringify(data));
console.log(`lib/dashboard.json: ${data.variances.length} variances, AI ${data.aiQuality?.version ?? "no evaluation"}`);
