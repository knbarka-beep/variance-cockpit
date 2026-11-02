import { data, type Variance } from "@/lib/data";
import { materialsSplit, millions, pct } from "@/lib/format";

type Props = {
  significant: { top: Variance[]; subRows: Map<string, Variance> };
  group: string | null;
  onClearGroup: () => void;
  onSelect: (id: string) => void;
};

export const STATUS: Record<string, string> = { approved: "Approved", edited: "Edited", rejected: "Rejected" };

/** Price/volume split for raw materials and packaging, so the list ties to the bridge. */
export function splitFor(v: Variance) {
  if (v.pl_group !== "Cost of materials") return null;
  const s = data.flexed.find((f) => f.period === v.period && f.account_no === v.account_no);
  return s ? materialsSplit(s) : null;
}

function Row({ v, onSelect, sub }: { v: Variance; onSelect: (id: string) => void; sub?: boolean }) {
  const split = splitFor(v);
  const name = `${v.account_no} ${v.account_name}${v.variance_type === "price" ? " (price effect)" : ""}`;
  return (
    <li className={sub ? "subrow" : undefined}>
      <button className="vrow" onClick={() => onSelect(v.variance_id)} aria-label={`${name}, ${v.cost_centre}: open details`}>
        <span className="line">
          <span className="name">{name}</span>
          <span className={`num ${v.favourable ? "fav" : "unfav"}`}>
            <span aria-hidden="true">{v.favourable ? "▲" : "▼"}</span> {millions(v.variance_profit_dkk)}
          </span>
        </span>
        <span className="line small muted">
          <span>{v.cost_centre} · {v.favourable ? "favourable" : "unfavourable"}</span>
          <span className="num">{pct(v.variance_pct)}{v.variance_type === "price" ? " vs flexed budget" : ""}</span>
        </span>
        {split && <span className="small">{split}</span>}
        <span className="small muted">
          AI: {v.ai_cause_category ?? "no draft"} · <span className="status">{v.review_status ? STATUS[v.review_status] : "Not reviewed"}</span>
        </span>
      </button>
    </li>
  );
}

export default function VarianceList({ significant, group, onClearGroup, onSelect }: Props) {
  const shown = significant.top.filter((v) => !group || v.pl_group === group);
  return (
    <section className="card" aria-labelledby="list-title">
      <div className="section-head">
        <h2 id="list-title">Significant variances ({significant.top.length})</h2>
        {group ? (
          <button className="chip" onClick={onClearGroup}>{group} ✕ <span className="sr-only">clear filter</span></button>
        ) : <p className="muted small">Largest first</p>}
      </div>
      {shown.length === 0 ? (
        <p className="muted">{group ? `No significant variances in ${group} this month.` : "No significant variances this month."}</p>
      ) : (
        <ul className="vlist">
          {shown.map((v) => [
            <Row key={v.variance_id} v={v} onSelect={onSelect} />,
            significant.subRows.has(v.cell_id) && (
              <Row key={`${v.variance_id}-sub`} v={significant.subRows.get(v.cell_id)!} onSelect={onSelect} sub />
            ),
          ])}
        </ul>
      )}
    </section>
  );
}
