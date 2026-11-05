"use client";
import { useEffect, useRef } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { data } from "@/lib/data";
import { amount, label, last12, millions, monthLabel, pct } from "@/lib/format";
import ChartTooltip from "./ChartTooltip";
import { splitFor, statusText } from "./VarianceList";

type Point = { period: string; actual?: number; budget?: number; base: string };
const trendTip = (p: Point) => ({ title: p.period, rows: [
  { label: "Actual", value: p.actual == null ? "–" : millions(p.actual) },
  { label: p.base, value: p.budget == null ? "–" : millions(p.budget) }] });

/** Details for one variance in a native <dialog>: focus trap and Esc to close come with it. */
export default function Drilldown({ id, onClose }: { id: string | null; onClose: () => void }) {
  const ref = useRef<HTMLDialogElement>(null);
  const v = id ? data.variances.find((x) => x.variance_id === id) : undefined;

  useEffect(() => {
    const d = ref.current;
    if (v && d && !d.open) d.showModal();
    if (!v && d?.open) d.close();
  }, [v]);

  const base = v?.variance_type === "price" ? "Flexed budget" : "Budget";
  // A price row is measured against the flexed budget, so its chart uses the same basis.
  const trend: Point[] = v ? last12(data.meta.periods, v.period).map((p) => {
    const r = v.variance_type === "price"
      ? data.flexed.find((f) => f.period === p && f.account_no === v.account_no)
      : data.accountMonth.find((a) => a.period === p && a.account_no === v.account_no && a.cost_centre === v.cost_centre);
    const budget = r && ("flexed_budget_dkk" in r ? r.flexed_budget_dkk : r.budget_dkk);
    return { period: monthLabel(p), actual: r?.actual_dkk, budget, base };
  }) : [];
  const lines = v ? data.transactions.filter((t) => t.cell_id === v.cell_id)
    .sort((a, b) => Math.abs(b.amount_dkk) - Math.abs(a.amount_dkk)) : [];
  const split = v && splitFor(v);

  return (
    <dialog ref={ref} className="drill" onClose={onClose} aria-labelledby="drill-title"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      {v && (
        <>
          <div className="sticky top-0 z-10 flex items-start justify-between gap-3 border-b border-border bg-surface px-5 py-4">
            <div>
              <h2 id="drill-title" className="t-section">{v.account_no} {v.account_name}{v.variance_type === "price" ? " (price effect)" : ""}</h2>
              <p className="t-small text-muted">{v.cost_centre} · {monthLabel(v.period)}</p>
            </div>
            <button type="button" className="btn icon" onClick={onClose} aria-label="Close details">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" aria-hidden="true"><path d="M4 4l8 8M12 4l-8 8" /></svg>
            </button>
          </div>
          <div className="grid gap-6 px-5 py-5">
            <dl className="grid grid-cols-3 gap-4">
              <div><dt className="t-label">Actual</dt><dd className="mt-1 text-lg font-semibold">{millions(v.actual_dkk)}</dd></div>
              <div><dt className="t-label">{base}</dt><dd className="mt-1 text-lg font-semibold">{millions(v.flexed_budget_dkk ?? v.budget_dkk)}</dd></div>
              <div><dt className="t-label">Variance</dt>
                <dd className={`mt-1 text-lg font-semibold ${v.favourable ? "fav" : "unfav"}`}>{millions(v.variance_profit_dkk)}</dd>
                <dd className={`t-small ${v.favourable ? "fav" : "unfav"}`}>{v.favourable ? "favourable" : "unfavourable"} ({pct(v.variance_pct)})</dd></div>
            </dl>
            {split && <p className="t-small">{split} The bridge shows all cost of materials together, including packaging.</p>}

            <div>
              <h3 className="t-label mb-2">Last 12 months, actual vs {base.toLowerCase()}</h3>
              <div style={{ height: 160 }} role="img" aria-label={`Actual (solid) and ${base.toLowerCase()} (dashed) for this account, last 12 months`}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={trend} margin={{ top: 8, right: 8, bottom: 0, left: 0 }} accessibilityLayer={false}>
                    <CartesianGrid stroke="var(--grid)" vertical={false} />
                    <XAxis dataKey="period" tickFormatter={(p: string) => p.slice(0, 3)} tick={{ fill: "var(--muted)", fontSize: 11 }} tickLine={false} axisLine={{ stroke: "var(--border-strong)" }} />
                    <YAxis tickFormatter={(x: number) => `${(x / 1e6).toFixed(1).replace(".", ",")}m`} tick={{ fill: "var(--muted)", fontSize: 11 }} width={40} axisLine={false} tickLine={false} />
                    <Tooltip cursor={{ stroke: "var(--border-strong)" }} isAnimationActive={false} content={<ChartTooltip<Point> render={trendTip} />} />
                    <Line dataKey="budget" stroke="var(--neutral)" strokeWidth={1.25} strokeDasharray="3 3" dot={false} activeDot={{ r: 3, fill: "var(--neutral)", stroke: "var(--surface)" }} isAnimationActive={false} />
                    <Line dataKey="actual" stroke="var(--accent)" strokeWidth={1.75} dot={{ r: 2, fill: "var(--accent)", stroke: "var(--accent)" }} activeDot={{ r: 4, fill: "var(--accent)", stroke: "var(--surface)" }} isAnimationActive={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div>
              <h3 className="t-label">AI draft</h3>
              {v.ai_comment ? (
                <>
                  <p className="quote mt-2">{v.ai_comment}</p>
                  <p className="t-small mt-1.5 text-muted">
                    Cause: {label(v.ai_cause_category)} · Persistence: {label(v.ai_persistence)} · Figure check:{" "}
                    {v.figure_check_passed ? "all figures found in the data" : "figures to check"} · {v.ai_model}, prompt {v.ai_prompt_version}
                  </p>
                </>
              ) : <p className="mt-2 text-muted">No AI draft for this variance.</p>}
            </div>

            <div>
              <h3 className="t-label">Review</h3>
              <p className="mt-2 font-semibold">{statusText(v)}</p>
              {v.final_comment && <p className="quote mt-2">{v.final_comment}</p>}
              {v.reviewer_note && <p className="t-small mt-1.5 text-muted">Note: {v.reviewer_note}</p>}
            </div>

            <div>
              <h3 className="t-label mb-1">Transactions ({lines.length})</h3>
              <div className="overflow-x-auto">
                <table className="data-table">
                  <thead><tr><th>Date</th><th>Counterparty</th><th className="desc-col">Description</th><th className="num">DKK</th></tr></thead>
                  <tbody>
                    {lines.map((t, i) => (
                      <tr key={i}>
                        <td className="whitespace-nowrap">{t.posting_date.slice(8, 10)}.{t.posting_date.slice(5, 7)}</td>
                        <td>{t.counterparty ?? "–"}<span className="desc-inline">{t.description}</span></td>
                        <td className="desc-col">{t.description}</td><td className="num">{amount(t.amount_dkk)}</td></tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </>
      )}
    </dialog>
  );
}
