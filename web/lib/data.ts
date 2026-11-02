// Typed access to lib/dashboard.json (written by scripts/prepare-data.mjs at build time).
import raw from "./dashboard.json";

export type Kpi = {
  period: string;
  revenue_actual_dkk: number; revenue_budget_dkk: number; revenue_variance_dkk: number; revenue_variance_pct: number;
  ebitda_actual_dkk: number; ebitda_budget_dkk: number; ebitda_variance_dkk: number; ebitda_variance_pct: number;
  ebitda_margin_actual_pct: number; ebitda_margin_budget_pct: number;
};
export type BridgeStep = {
  period: string; step_no: number; step: string; step_type: string;
  amount_dkk: number; bar_start_dkk: number; bar_end_dkk: number;
};
export type AccountMonth = {
  period: string; account_no: number; account_name: string; pl_group: string; cost_centre: string;
  actual_dkk: number; budget_dkk: number; variance_profit_dkk: number;
};
export type Flexed = {
  period: string; account_no: number; account_name: string; actual_dkk: number; flexed_budget_dkk: number; volume_pct_of_budget: number;
  total_variance_profit_dkk: number; price_usage_variance_profit_dkk: number; volume_variance_profit_dkk: number;
};
export type Transaction = { cell_id: string; posting_date: string; counterparty: string | null; description: string; amount_dkk: number };
export type Variance = {
  variance_id: string; variance_type: string; cell_id: string; period: string; rank_in_month: number;
  account_no: number; account_name: string; pl_group: string; cost_centre: string;
  actual_dkk: number; budget_dkk: number; flexed_budget_dkk: number | null;
  variance_profit_dkk: number; variance_pct: number; favourable: boolean;
  ai_comment?: string; ai_cause_category?: string; ai_persistence?: string; figure_check_passed?: boolean;
  ai_model?: string; ai_prompt_version?: string;
  review_status?: string | null; final_comment?: string | null; reviewer_note?: string | null;
};
export type AiQuality = {
  version: string; models: string[]; drafts: number; figure_check_passed: number;
  planted_correct: number; planted_total: number; noise_false_claims: number; noise_drafted: number;
} | null;
export type Dashboard = {
  meta: { company_name: string; notice: string; periods: string[]; latest_period: string;
    materiality: { min_pct: number; min_amount_dkk: number } };
  kpis: Kpi[]; bridge: BridgeStep[]; accountMonth: AccountMonth[]; flexed: Flexed[];
  transactions: Transaction[]; variances: Variance[]; aiQuality: AiQuality;
  monthSummaries: Record<string, string>; // the controller's sentence per month; missing = not shown
};

export const data = raw as unknown as Dashboard;
