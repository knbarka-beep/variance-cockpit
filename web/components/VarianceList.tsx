import { data, type Variance } from "@/lib/data";
import { label, materialsSplit, millions, pct } from "@/lib/format";
import { Card, CardHeader } from "./kit/Card";

type Props = {
  significant: { top: Variance[]; subRows: Map<string, Variance> };
  group: string | null;
  onClearGroup: () => void;
  onSelect: (id: string) => void;
};

export const STATUS: Record<string, string> = { approved: "Approved", edited: "Edited", rejected: "Rejected" };
export const REVIEWER: Record<string, string> = { claude: "suggested by Claude", knut: "checked by Knut" };
/** "Approved (suggested by Claude)", or "Not reviewed". */
export const statusText = (v: Variance) =>
  v.review_status ? `${STATUS[v.review_status]}${v.reviewed_by ? ` (${REVIEWER[v.reviewed_by]})` : ""}` : "Not reviewed";

/** Price/volume split for raw materials and packaging, so the list ties to the bridge. */
export function splitFor(v: Variance) {
  if (v.pl_group !== "Cost of materials") return null;
  const s = data.flexed.find((f) => f.period === v.period && f.account_no === v.account_no);
  return s ? materialsSplit(s) : null;
}

/** When an account row has a price-effect sub-row, the account row carries the AI label and status and the
 *  sub-row carries the price/volume split, so nothing is shown twice. Each row still opens its own draft. */
function Row({ v, onSelect, sub, hasSub }: { v: Variance; onSelect: (id: string) => void; sub?: boolean; hasSub?: boolean }) {
  const split = hasSub ? null : splitFor(v);
  const name = `${v.account_no} ${v.account_name}${v.variance_type === "price" ? " (price effect)" : ""}`;
  return (
    <li className={sub ? "subrow" : undefined}>
      <button type="button" className="vrow" onClick={() => onSelect(v.variance_id)} aria-label={`${name}, ${v.cost_centre}: open details`}>
        <span className="line">
          <span className="font-medium">{name}</span>
          <span className={`num font-semibold ${v.favourable ? "fav" : "unfav"}`}>{millions(v.variance_profit_dkk)}</span>
        </span>
        <span className="line t-small text-muted">
          <span>{v.cost_centre} · {v.favourable ? "favourable" : "unfavourable"}</span>
          <span className="num">{pct(v.variance_pct)}{v.variance_type === "price" ? " vs flexed budget" : ""}</span>
        </span>
        {split && <span className="t-small">{split}</span>}
        {!sub && (
          <span className="t-small text-muted">
            AI: {v.ai_cause_category ? label(v.ai_cause_category) : "No draft"} · <span className="status">{statusText(v)}</span>
          </span>
        )}
      </button>
    </li>
  );
}

export default function VarianceList({ significant, group, onClearGroup, onSelect }: Props) {
  const shown = significant.top.filter((v) => !group || v.pl_group === group);
  return (
    <Card aria-labelledby="list-title">
      <CardHeader id="list-title" title={`Significant variances (${significant.top.length})`}
        aside={group ? (
          <button type="button" className="btn" onClick={onClearGroup}>{group} only · show all</button>
        ) : "Largest first"} />
      {shown.length === 0 ? (
        <p className="text-muted">{group ? `No significant variances in ${group} this month.` : "No significant variances this month."}</p>
      ) : (
        <ul className="vlist">
          {shown.map((v) => [
            <Row key={v.variance_id} v={v} onSelect={onSelect} hasSub={significant.subRows.has(v.cell_id)} />,
            significant.subRows.has(v.cell_id) && (
              <Row key={`${v.variance_id}-sub`} v={significant.subRows.get(v.cell_id)!} onSelect={onSelect} sub />
            ),
          ])}
        </ul>
      )}
    </Card>
  );
}
