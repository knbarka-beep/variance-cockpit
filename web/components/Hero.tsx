import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip } from "recharts";
import { data, type Kpi, type Variance } from "@/lib/data";
import { direction, last12, millions, monthLabel, pct } from "@/lib/format";
import { InfoTip } from "./kit/InfoTip";
import { KpiCard } from "./kit/KpiCard";
import ChartTooltip from "./ChartTooltip";

const revenueTip = (k: Kpi) => ({ title: monthLabel(k.period), rows: [
  { label: "Actual", value: millions(k.revenue_actual_dkk) }, { label: "Budget", value: millions(k.revenue_budget_dkk) }] });

type Props = { period: string; significant: { top: Variance[]; count: number; accounts: number; priceEffects: number } };

/** The answer first: EBITDA against budget for the month, the two largest variances behind it,
 *  then revenue, margin and the number of significant variances. */
export default function Hero({ period, significant }: Props) {
  const k = data.kpis.find((r) => r.period === period);
  if (!k) return <p className="text-muted">No figures for this month.</p>;
  const trend = last12(data.meta.periods, period).map((p) => data.kpis.find((r) => r.period === p)!);
  const fav = k.ebitda_variance_dkk >= 0;
  const marginDiff = k.ebitda_margin_actual_pct - k.ebitda_margin_budget_pct;
  const { materiality } = data.meta;
  const drivers = significant.top.slice(0, 2);
  const name = (v: Variance) => `${v.account_no} ${v.account_name}${v.variance_type === "price" ? " (price effect)" : ""}`;

  return (
    <section aria-labelledby="hero-title" className="grid gap-x-12 gap-y-8 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:items-end">
      <div>
        <div className="flex items-center gap-1.5">
          <h2 id="hero-title" className="t-label">EBITDA vs budget, {monthLabel(period)}</h2>
          <InfoTip label="EBITDA vs budget">
            <p>EBITDA: revenue minus cost of materials, staff costs and other operating expenses.</p>
            <p>The bridge below shows how each of these groups moves EBITDA from budget to actual.</p>
          </InfoTip>
        </div>
        <p className="mt-2 flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <span className="t-hero">{millions(k.ebitda_variance_dkk)}</span>
          <span className="font-serif text-[1.75rem] leading-none">{fav ? "above" : "below"} budget</span>
          <span className={`delta ${fav ? "good" : "bad"} self-center`}><span aria-hidden="true">{fav ? "↑" : "↓"}</span> {pct(k.ebitda_variance_pct)}</span>
        </p>
        <p className="mt-3 max-w-[52ch] text-[0.95rem]">
          EBITDA <b className="font-semibold">{millions(k.ebitda_actual_dkk)}</b> against a budget of{" "}
          <b className="font-semibold">{millions(k.ebitda_budget_dkk)}</b>.
          {drivers.length > 0 && (
            <> Largest significant variance{drivers.length > 1 ? "s" : ""}:{" "}
              {drivers.map((v, i) => (
                <span key={v.variance_id}>{i > 0 && " and "}{name(v)} ({millions(v.variance_profit_dkk)} {direction(v.favourable).toLowerCase()})</span>
              ))}.</>
          )}
        </p>
      </div>

      <div className="kpis grid gap-x-8 gap-y-6 sm:grid-cols-3">
        <KpiCard label="Revenue" value={millions(k.revenue_actual_dkk)}
          change={{ text: `${millions(k.revenue_variance_dkk)} (${pct(k.revenue_variance_pct)})`, up: k.revenue_variance_dkk >= 0,
            good: k.revenue_variance_dkk >= 0, vs: "budget" }}>
          <p className="t-small text-muted">Budget {millions(k.revenue_budget_dkk)}</p>
          <div className="h-10" role="img" aria-label="Revenue, last 12 months: actual (solid) against budget (dashed)">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trend} margin={{ top: 4, right: 2, bottom: 2, left: 2 }} accessibilityLayer={false}>
                <CartesianGrid stroke="var(--grid)" vertical={false} />
                <Tooltip cursor={{ stroke: "var(--border-strong)" }} isAnimationActive={false} wrapperStyle={{ zIndex: 5 }}
                  content={<ChartTooltip<Kpi> render={revenueTip} />} />
                <Line dataKey="revenue_budget_dkk" stroke="var(--neutral)" strokeDasharray="3 3" dot={false} strokeWidth={1.25}
                  activeDot={{ r: 3, fill: "var(--neutral)", strokeWidth: 0 }} isAnimationActive={false} />
                <Line dataKey="revenue_actual_dkk" stroke="var(--accent)" dot={false} strokeWidth={1.75}
                  activeDot={{ r: 3, fill: "var(--accent)", strokeWidth: 0 }} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </KpiCard>
        <KpiCard label="EBITDA margin" value={pct(k.ebitda_margin_actual_pct)}
          change={{ text: `${Math.abs(marginDiff).toFixed(1).replace(".", ",")} pp`, up: marginDiff >= 0, good: marginDiff >= 0,
            vs: "budget" }}>
          <p className="t-small text-muted">Budget {pct(k.ebitda_margin_budget_pct)}</p>
        </KpiCard>
        <KpiCard label="Significant variances" value={`${significant.count}`}
          info={<p>A variance is significant when it is at least {materiality.min_pct.toLocaleString("da-DK")} % and
            DKK {materiality.min_amount_dkk.toLocaleString("da-DK")} from budget, per account and month.</p>}>
          {significant.priceEffects > 0 && (
            <p className="t-small text-muted">{significant.accounts} accounts + {significant.priceEffects} price effect{significant.priceEffects > 1 ? "s" : ""}</p>
          )}
        </KpiCard>
      </div>
    </section>
  );
}
