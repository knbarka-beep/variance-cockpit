"use client";
import { useEffect, useRef } from "react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { data } from "@/lib/data";
import { amount, label, last12, millions, monthLabel, pct } from "@/lib/format";
import ChartTooltip from "./ChartTooltip";

type Point = { period: string; actual?: number; budget?: number };
const trendTip = (p: Point) => ({ title: p.period, rows: [
  { label: "Actual", value: p.actual == null ? "–" : millions(p.actual) },
  { label: "Budget", value: p.budget == null ? "–" : millions(p.budget) }] });
import { STATUS, splitFor } from "./VarianceList";

/** Details for one variance in a native <dialog>: focus trap and Esc to close come with it. */
export default function Drilldown({ id, onClose }: { id: string | null; onClose: () => void }) {
  const ref = useRef<HTMLDialogElement>(null);
  const v = id ? data.variances.find((x) => x.variance_id === id) : undefined;

  useEffect(() => {
    const d = ref.current;
    if (v && d && !d.open) d.showModal();
    if (!v && d?.open) d.close();
  }, [v]);

  const trend = v ? last12(data.meta.periods, v.period).map((p) => {
    const r = data.accountMonth.find((a) => a.period === p && a.account_no === v.account_no && a.cost_centre === v.cost_centre);
    return { period: monthLabel(p), actual: r?.actual_dkk, budget: r?.budget_dkk };
  }) : [];
  const lines = v ? data.transactions.filter((t) => t.cell_id === v.cell_id)
    .sort((a, b) => Math.abs(b.amount_dkk) - Math.abs(a.amount_dkk)) : [];
  const split = v && splitFor(v);
  const base = v?.variance_type === "price" ? "Flexed budget" : "Budget";

  return (
    <dialog ref={ref} className="drill" onClose={onClose} aria-labelledby="drill-title"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      {v && (
        <>
          <div className="drill-head">
            <div>
              <h2 id="drill-title">{v.account_no} {v.account_name}{v.variance_type === "price" ? " (price effect)" : ""}</h2>
              <p className="muted small">{v.cost_centre} · {monthLabel(v.period)}</p>
            </div>
            <button className="iconbtn" onClick={onClose} aria-label="Close details">✕</button>
          </div>
          <div className="drill-body">
            <div className="facts">
              <span>Actual <b>{millions(v.actual_dkk)}</b></span>
              <span>{base} <b>{millions(v.flexed_budget_dkk ?? v.budget_dkk)}</b></span>
              <span className={v.favourable ? "fav" : "unfav"}>
                <b>{millions(v.variance_profit_dkk)} {v.favourable ? "favourable" : "unfavourable"}</b> ({pct(v.variance_pct)})
              </span>
            </div>
            {split && <p>{split} The bridge shows all cost of materials together, including packaging.</p>}

            <div>
              <h3>Last 12 months, actual vs budget</h3>
              <div style={{ height: 160 }} role="img" aria-label="Actual (solid) and budget (dashed) for this account, last 12 months">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={trend} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
                    <XAxis dataKey="period" tickFormatter={(p: string) => p.slice(0, 3)} tick={{ fill: "var(--muted)", fontSize: 11 }} tickLine={false} axisLine={{ stroke: "var(--border)" }} />
                    <YAxis tickFormatter={(x: number) => `${(x / 1e6).toFixed(1).replace(".", ",")}m`} tick={{ fill: "var(--muted)", fontSize: 11 }} width={40} axisLine={false} tickLine={false} />
                    <Tooltip cursor={{ stroke: "var(--border)" }} content={<ChartTooltip<Point> render={trendTip} />} />
                    <Line dataKey="budget" stroke="var(--budget)" strokeDasharray="3 3" dot={false} activeDot={{ r: 3, fill: "var(--budget)", stroke: "var(--surface)" }} isAnimationActive={false} />
                    <Line dataKey="actual" stroke="var(--accent)" strokeWidth={2} dot={{ r: 2, fill: "var(--accent)", stroke: "var(--accent)" }} activeDot={{ r: 4, fill: "var(--accent)", stroke: "var(--surface)" }} isAnimationActive={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div>
              <h3>AI draft</h3>
              {v.ai_comment ? (
                <>
                  <p className="quote" style={{ marginTop: 8 }}>{v.ai_comment}</p>
                  <p className="small muted" style={{ marginTop: 4 }}>
                    Cause: {label(v.ai_cause_category)} · Persistence: {label(v.ai_persistence)} · Figure check:{" "}
                    {v.figure_check_passed ? "all figures found in the data" : "figures to check"} · {v.ai_model}, prompt {v.ai_prompt_version}
                  </p>
                </>
              ) : <p className="muted">No AI draft for this variance.</p>}
            </div>

            <div>
              <h3>Controller review</h3>
              <p style={{ marginTop: 8 }}><b>{v.review_status ? STATUS[v.review_status] : "Not reviewed yet"}</b></p>
              {v.final_comment && <p className="quote" style={{ marginTop: 4 }}>{v.final_comment}</p>}
              {v.reviewer_note && <p className="small muted">Note: {v.reviewer_note}</p>}
            </div>

            <div>
              <h3>Transactions ({lines.length})</h3>
              <div className="tablewrap">
                <table>
                  <thead><tr><th>Date</th><th>Counterparty</th><th>Description</th><th className="num">DKK</th></tr></thead>
                  <tbody>
                    {lines.map((t, i) => (
                      <tr key={i}><td>{t.posting_date}</td><td>{t.counterparty ?? "–"}</td><td>{t.description}</td><td className="num">{amount(t.amount_dkk)}</td></tr>
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
