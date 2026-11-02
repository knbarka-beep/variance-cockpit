"use client";
import { useState } from "react";
import { data } from "@/lib/data";
import { groupSignificant, monthLabel } from "@/lib/format";
import KpiRow from "./KpiRow";
import Bridge from "./Bridge";
import VarianceList from "./VarianceList";
import Drilldown from "./Drilldown";
import AiQuality from "./AiQuality";
import ThemeToggle from "./ThemeToggle";

const DEFAULT_PERIOD = "2026-09";

export default function Dashboard() {
  const { meta } = data;
  const [period, setPeriod] = useState(meta.periods.includes(DEFAULT_PERIOD) ? DEFAULT_PERIOD : meta.latest_period);
  const [group, setGroup] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);

  const rows = data.variances
    .filter((v) => v.period === period)
    .sort((a, b) => Math.abs(b.variance_profit_dkk) - Math.abs(a.variance_profit_dkk));
  const significant = groupSignificant(rows);
  const i = meta.periods.indexOf(period);
  const go = (p: string) => { setPeriod(p); setGroup(null); };

  return (
    <div className="page">
      <header className="header">
        <div>
          <h1>Variance Cockpit</h1>
          <p className="muted small">{meta.company_name} · month-end close, budget vs actual</p>
        </div>
        <div className="controls">
          <button className="iconbtn" aria-label="Previous month" disabled={i <= 0} onClick={() => go(meta.periods[i - 1])}>‹</button>
          <label className="sr-only" htmlFor="period">Month</label>
          <select id="period" value={period} onChange={(e) => go(e.target.value)}>
            {meta.periods.map((p) => <option key={p} value={p}>{monthLabel(p)}</option>)}
          </select>
          <button className="iconbtn" aria-label="Next month" disabled={i >= meta.periods.length - 1} onClick={() => go(meta.periods[i + 1])}>›</button>
          <ThemeToggle />
        </div>
      </header>
      <p className="notice" role="note">
        Synthetic data. The company, its customers and suppliers are fictional; any resemblance to real companies is coincidental.
      </p>

      <KpiRow period={period} significant={significant} />

      <div className="main">
        <Bridge period={period} group={group} onGroup={setGroup} />
        <VarianceList significant={significant} group={group} onClearGroup={() => setGroup(null)} onSelect={setSelected} />
      </div>

      <AiQuality />

      <footer>
        Significant variance: at least {meta.materiality.min_pct.toLocaleString("da-DK")} % and DKK{" "}
        {meta.materiality.min_amount_dkk.toLocaleString("da-DK")} from budget, per account, cost centre and month.
        AI comments are drafts written once and stored; this page never calls an AI model.{" "}
        <a href="https://github.com/knbarka-beep/variance-cockpit">Method and limitations on GitHub</a>.
      </footer>

      <Drilldown id={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
