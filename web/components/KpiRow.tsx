import { Line, LineChart, ResponsiveContainer } from "recharts";
import { data } from "@/lib/data";
import { direction, last12, millions, pct } from "@/lib/format";

type Props = { period: string; significant: { count: number; accounts: number; priceEffects: number } };

function Delta({ favourable, children }: { favourable: boolean; children: React.ReactNode }) {
  return (
    <p className={`delta ${favourable ? "fav" : "unfav"}`}>
      <span aria-hidden="true">{favourable ? "▲" : "▼"}</span> {children} · {direction(favourable)}
    </p>
  );
}

export default function KpiRow({ period, significant }: Props) {
  const k = data.kpis.find((r) => r.period === period);
  if (!k) return <p className="card">No figures for this month.</p>;
  const trend = last12(data.meta.periods, period).map((p) => data.kpis.find((r) => r.period === p)!);
  const marginDiff = k.ebitda_margin_actual_pct - k.ebitda_margin_budget_pct;
  const { materiality } = data.meta;

  return (
    <section className="kpis" aria-label="Key figures">
      <div className="card kpi">
        <h3>Revenue</h3>
        <p className="value">{millions(k.revenue_actual_dkk)}</p>
        <p className="muted small">Budget {millions(k.revenue_budget_dkk)}</p>
        <Delta favourable={k.revenue_variance_dkk >= 0}>{millions(k.revenue_variance_dkk)} ({pct(k.revenue_variance_pct)})</Delta>
        <div style={{ height: 36 }} role="img" aria-label="Revenue, last 12 months: actual (solid) against budget (dashed)">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={trend} margin={{ top: 4, right: 2, bottom: 2, left: 2 }}>
              <Line dataKey="revenue_budget_dkk" stroke="var(--budget)" strokeDasharray="3 3" dot={false} strokeWidth={1.5} isAnimationActive={false} />
              <Line dataKey="revenue_actual_dkk" stroke="var(--accent)" dot={false} strokeWidth={2} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <p className="muted small">12 months, actual vs budget</p>
      </div>
      <div className="card kpi">
        <h3>EBITDA</h3>
        <p className="value">{millions(k.ebitda_actual_dkk)}</p>
        <p className="muted small">Budget {millions(k.ebitda_budget_dkk)}</p>
        <Delta favourable={k.ebitda_variance_dkk >= 0}>{millions(k.ebitda_variance_dkk)} ({pct(k.ebitda_variance_pct)})</Delta>
      </div>
      <div className="card kpi">
        <h3>EBITDA margin</h3>
        <p className="value">{pct(k.ebitda_margin_actual_pct)}</p>
        <p className="muted small">Budget {pct(k.ebitda_margin_budget_pct)}</p>
        <Delta favourable={marginDiff >= 0}>{Math.abs(marginDiff).toFixed(1).replace(".", ",")} pp</Delta>
      </div>
      <div className="card kpi">
        <h3>Significant variances</h3>
        <p className="value">{significant.count}</p>
        {significant.priceEffects > 0 && (
          <p className="small">{significant.accounts} accounts + {significant.priceEffects} price effect{significant.priceEffects > 1 ? "s" : ""}</p>
        )}
        <p className="muted small">
          At least {materiality.min_pct.toLocaleString("da-DK")} % and DKK {materiality.min_amount_dkk.toLocaleString("da-DK")}, per account and month
        </p>
      </div>
    </section>
  );
}
