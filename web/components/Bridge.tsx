import { Bar, BarChart, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { data } from "@/lib/data";
import { direction, millions, monthLabel } from "@/lib/format";

const SHORT: Record<string, string> = {
  "Budget EBITDA": "Budget", Revenue: "Revenue", "Cost of materials": "Materials",
  "Staff costs": "Staff", "Other operating expenses": "Other opex", "Actual EBITDA": "Actual",
};
const groupOf = (step: string) => step; // change steps are named after their P&L group

type Props = { period: string; group: string | null; onGroup: (g: string | null) => void };

export default function Bridge({ period, group, onGroup }: Props) {
  const steps = data.bridge.filter((s) => s.period === period).sort((a, b) => a.step_no - b.step_no)
    .map((s) => ({ ...s, label: SHORT[s.step] ?? s.step, range: [s.bar_start_dkk, s.bar_end_dkk] }));
  const kind = (s: (typeof steps)[number]) => s.step_type === "total" ? "total" : s.amount_dkk >= 0 ? "fav" : "unfav";

  return (
    <section className="card" aria-labelledby="bridge-title">
      <div className="section-head">
        <h2 id="bridge-title">EBITDA bridge: budget to actual, {monthLabel(period)}</h2>
        <p className="muted small">Click a bar to filter the list</p>
      </div>
      <div style={{ height: 340 }} aria-hidden="true">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={steps} margin={{ top: 24, right: 8, bottom: 0, left: 0 }}>
            <XAxis dataKey="label" tick={{ fill: "var(--muted)", fontSize: 12 }} interval={0} tickLine={false} axisLine={{ stroke: "var(--border)" }} />
            <YAxis tickFormatter={(v: number) => `${(v / 1e6).toFixed(1).replace(".", ",")}m`} tick={{ fill: "var(--muted)", fontSize: 12 }} width={44} axisLine={false} tickLine={false} />
            <Tooltip
              cursor={{ fill: "var(--accent-soft)" }}
              contentStyle={{ background: "var(--surface)", border: "1px solid var(--border)", color: "var(--text)" }}
              formatter={(_v, _n, item) => {
                const s = item.payload as (typeof steps)[number];
                return [s.step_type === "total" ? millions(s.amount_dkk) : `${millions(s.amount_dkk)} ${direction(s.amount_dkk >= 0).toLowerCase()}`, s.step];
              }}
              labelFormatter={() => ""}
            />
            <Bar dataKey="range" isAnimationActive={false} cursor="pointer"
              onClick={(d) => { const s = d.payload as (typeof steps)[number]; if (s.step_type !== "total") onGroup(groupOf(s.step)); }}>
              {steps.map((s) => (
                <Cell key={s.step_no} className={`bar bar-${kind(s)}`}
                  opacity={group && s.step_type !== "total" && groupOf(s.step) !== group ? 0.35 : 1} />
              ))}
              <LabelList dataKey="amount_dkk" position="top" fontSize={12} fill="var(--text)"
                formatter={(v) => `${Number(v) < 0 ? "−" : ""}${(Math.abs(Number(v)) / 1e6).toFixed(2).replace(".", ",")}m`} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      {/* The same numbers as text, for screen readers and keyboard users */}
      <table className="sr-only">
        <caption>EBITDA bridge, {monthLabel(period)}</caption>
        <tbody>
          {steps.map((s) => (
            <tr key={s.step_no}><th scope="row">{s.step}</th><td>{millions(s.amount_dkk)}{s.step_type !== "total" && ` ${direction(s.amount_dkk >= 0).toLowerCase()}`}</td></tr>
          ))}
        </tbody>
      </table>
      <div className="facts small muted" style={{ marginTop: 8 }}>
        {steps.filter((s) => s.step_type !== "total").map((s) => (
          <button key={s.step_no} className="chip" aria-pressed={group === groupOf(s.step)}
            onClick={() => onGroup(group === groupOf(s.step) ? null : groupOf(s.step))}>
            {SHORT[s.step]}
          </button>
        ))}
      </div>
    </section>
  );
}
