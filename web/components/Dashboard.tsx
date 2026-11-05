"use client";
import { useState } from "react";
import { data } from "@/lib/data";
import { groupSignificant, monthLabel } from "@/lib/format";
import Hero from "./Hero";
import Bridge from "./Bridge";
import VarianceList from "./VarianceList";
import Drilldown from "./Drilldown";
import AiQuality from "./AiQuality";
import { InfoTip } from "./kit/InfoTip";
import { PageHeader } from "./kit/PageHeader";
import { ThemeToggle } from "./kit/ThemeToggle";

const DEFAULT_PERIOD = "2026-09";
const Chevron = ({ d }: { d: string }) => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={d} /></svg>
);

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
  const summary = data.monthSummaries[period];
  const go = (p: string) => { setPeriod(p); setGroup(null); };
  // The company name already ends in "(fictional)"; the header shows it in two weights.
  const company = meta.company_name.replace(/ \(fictional\)$/, "");

  return (
    <>
      <PageHeader title="Variance Cockpit" suffix={`· ${company} (fictional)`}>
        <button type="button" className="btn icon" aria-label="Previous month" disabled={i <= 0} onClick={() => go(meta.periods[i - 1])}>
          <Chevron d="M10 3.5 5.5 8l4.5 4.5" />
        </button>
        <label className="sr-only" htmlFor="period">Month</label>
        <select id="period" value={period} onChange={(e) => go(e.target.value)}>
          {meta.periods.map((p) => <option key={p} value={p}>{monthLabel(p)}</option>)}
        </select>
        <button type="button" className="btn icon" aria-label="Next month" disabled={i >= meta.periods.length - 1} onClick={() => go(meta.periods[i + 1])}>
          <Chevron d="M6 3.5 10.5 8 6 12.5" />
        </button>
        <ThemeToggle />
      </PageHeader>

      <main className="mx-auto grid max-w-[1200px] gap-8 px-4 pt-6 pb-4">
        <div className="t-small flex items-center gap-1.5 text-muted" role="note">
          <span>Month-end close, budget vs actual. All company data on this page is synthetic.</span>
          <InfoTip label="the synthetic data">
            <p>Synthetic data. The company, its customers and suppliers are fictional; any resemblance to real companies is coincidental.</p>
          </InfoTip>
        </div>

        <Hero period={period} significant={significant} />

        {summary && (
          <section aria-labelledby="summary-title" className="grid gap-x-12 gap-y-1 border-y border-border py-4 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
            <h2 id="summary-title" className="t-label pt-0.5">{summary.author === "claude-draft" ? "Draft summary (Claude)" : "Controller's summary"}</h2>
            <p className="max-w-[75ch]">{summary.text}</p>
          </section>
        )}

        <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
          <Bridge period={period} group={group} onGroup={setGroup} />
          <VarianceList significant={significant} group={group} onClearGroup={() => setGroup(null)} onSelect={setSelected} />
        </div>

        <AiQuality />

        <Drilldown id={selected} onClose={() => setSelected(null)} />
      </main>

    </>
  );
}
