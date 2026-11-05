import { useSyncExternalStore } from "react";
import { Bar, BarChart, CartesianGrid, Cell, LabelList, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { data } from "@/lib/data";
import { direction, millions, monthLabel, signed } from "@/lib/format";
import ChartTooltip, { type TooltipContent } from "./ChartTooltip";
import { Card, CardHeader } from "./kit/Card";
import { SegmentedControl } from "./kit/SegmentedControl";
import { useAnimateOnce } from "./kit/useAnimateOnce";

const SHORT: Record<string, string> = {
  "Budget EBITDA": "Budget", Revenue: "Revenue", "Cost of materials": "Materials",
  "Staff costs": "Staff", "Other operating expenses": "Other opex", "Actual EBITDA": "Actual",
};
// Phones: the bars are about 45 px wide, so the axis labels are tilted.
const NARROW = "(max-width: 599px)";
const useNarrow = () => useSyncExternalStore(
  (cb) => { const m = matchMedia(NARROW); m.addEventListener("change", cb); return () => m.removeEventListener("change", cb); },
  () => matchMedia(NARROW).matches, () => false);
const groupOf = (step: string) => step; // change steps are named after their P&L group

/** The accounts behind one bar (summed over cost centres), so the parts add up to the bar. */
function accountsIn(period: string, group: string) {
  const sums = new Map<string, number>();
  for (const r of data.accountMonth) {
    if (r.period === period && r.pl_group === group) {
      sums.set(r.account_name, (sums.get(r.account_name) ?? 0) + r.variance_profit_dkk);
    }
  }
  return [...sums].sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]));
}

type Props = { period: string; group: string | null; onGroup: (g: string | null) => void };

export default function Bridge({ period, group, onGroup }: Props) {
  const steps = data.bridge.filter((s) => s.period === period).sort((a, b) => a.step_no - b.step_no)
    .map((s) => ({ ...s, label: SHORT[s.step] ?? s.step, range: [s.bar_start_dkk, s.bar_end_dkk] }));
  type Step = (typeof steps)[number];
  const tip = (s: Step): TooltipContent => {
    if (s.step_type === "total") return { title: s.step, rows: [{ label: "DKK", value: signed(s.amount_dkk) }] };
    const parts = accountsIn(period, s.step);
    return {
      title: `${s.step}: ${direction(s.amount_dkk >= 0).toLowerCase()}`,
      rows: [...parts.map(([name, v]) => ({ label: name, value: signed(v) })),
        ...(parts.length > 1 ? [{ label: "Total", value: signed(s.amount_dkk), strong: true }] : [])],
    };
  };
  const narrow = useNarrow();
  // The bars grow once on load (CSS, class removed after 500 ms), never again when the month or filter changes.
  // Recharts' own animation is off because it hides the value labels until it ends.
  const animate = useAnimateOnce();
  const changes = steps.filter((s) => s.step_type !== "total");
  const kind = (s: Step) => s.step_type === "total" ? "total" : s.amount_dkk >= 0 ? "fav" : "unfav";

  return (
    <Card large className="bridge-card" aria-labelledby="bridge-title">
      <CardHeader id="bridge-title" title={`EBITDA bridge, ${monthLabel(period)}`} aside="Click a bar to filter the list"
        info={<>
          <p>From budget EBITDA (left) to actual EBITDA (right). Each bar in between is one P&amp;L group&apos;s variance in
            profit terms: green is favourable, red unfavourable. Hover a bar to see the accounts behind it.</p>
          <p>Cost of materials includes packaging.</p>
        </>} />
      <div style={{ height: 340 }} aria-hidden="true" className={animate ? "bars-in" : undefined}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={steps} margin={{ top: 24, right: 8, bottom: 0, left: 0 }} accessibilityLayer={false}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="label" tick={{ fill: "var(--muted)", fontSize: narrow ? 11 : 12 }} interval={0}
              angle={narrow ? -35 : 0} textAnchor={narrow ? "end" : "middle"} height={narrow ? 56 : 30} tickLine={false} axisLine={{ stroke: "var(--border-strong)" }} />
            <YAxis tickFormatter={(v: number) => `${(v / 1e6).toFixed(1).replace(".", ",")}m`} tick={{ fill: "var(--muted)", fontSize: 12 }} width={44} axisLine={false} tickLine={false} />
            <Tooltip cursor={{ fill: "var(--surface-2)" }} isAnimationActive={false} content={<ChartTooltip<Step> render={tip} />} />
            {/* Dashed connectors: the level after each step, carried to the next bar */}
            {steps.slice(0, -1).map((s, i) => (
              <ReferenceLine key={s.step_no} stroke="var(--neutral)" strokeDasharray="3 3" strokeWidth={1}
                segment={[{ x: s.label, y: s.bar_end_dkk },
                  { x: steps[i + 1].label, y: s.bar_end_dkk }]} />
            ))}
            <Bar dataKey="range" isAnimationActive={false} cursor="pointer" radius={2}
              onClick={(d) => { const s = d.payload as (typeof steps)[number]; if (s.step_type !== "total") onGroup(groupOf(s.step)); }}>
              {steps.map((s) => (
                <Cell key={s.step_no} className={`bar bar-${kind(s)}`}
                  opacity={group && s.step_type !== "total" && groupOf(s.step) !== group ? 0.35 : 1} />
              ))}
              <LabelList dataKey="amount_dkk" position="top" fontSize={narrow ? 10 : 12} fill="var(--text)" fontWeight={500}
                formatter={(v) => `${Number(v) < 0 ? "−" : ""}${(Math.abs(Number(v)) / 1e6).toFixed(2).replace(".", ",")}m`} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      {/* The same numbers as text, for screen readers and keyboard users */}
      <div className="sr-only"><table>
        <caption>EBITDA bridge, {monthLabel(period)}</caption>
        <tbody>
          {steps.map((s) => (
            <tr key={s.step_no}><th scope="row">{s.step}</th><td>{millions(s.amount_dkk)}{s.step_type !== "total" && ` ${direction(s.amount_dkk >= 0).toLowerCase()}`}</td></tr>
          ))}
        </tbody>
      </table></div>
      <SegmentedControl className="mt-3" label="Filter the list by P&L group" options={["All", ...changes.map((s) => SHORT[s.step])]}
        value={group ? SHORT[group] : "All"}
        onChange={(o) => onGroup(o === "All" ? null : changes.find((s) => SHORT[s.step] === o)?.step ?? null)} />
    </Card>
  );
}