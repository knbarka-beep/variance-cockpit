// Pure helpers: number format and the grouping of significant variances. Tested in format.test.ts.

/** DKK 0,24m (European format, no sign: direction is given in words). */
export const millions = (v: number) => `DKK ${(Math.abs(v) / 1e6).toFixed(2).replace(".", ",")}m`;

/** 236.321 with a minus sign when negative (ledger lines can be credits). */
export const amount = (v: number) =>
  `${v < 0 ? "−" : ""}${Math.round(Math.abs(v)).toLocaleString("da-DK")}`;

/** 8,9 % */
export const pct = (v: number, decimals = 1) => `${Math.abs(v).toFixed(decimals).replace(".", ",")} %`;

export const direction = (favourable: boolean) => (favourable ? "Favourable" : "Unfavourable");

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
/** "2026-09" -> "Sep 2026" */
export const monthLabel = (period: string) => `${MONTHS[Number(period.slice(5, 7)) - 1]} ${period.slice(0, 4)}`;

/** The 12 periods ending with `period` (fewer at the start of the data). */
export const last12 = (periods: string[], period: string) =>
  periods.slice(Math.max(0, periods.indexOf(period) - 11), periods.indexOf(period) + 1);

type Row = { variance_id: string; variance_type: string; cell_id: string };

/** Significant variances are counted per account and month. A price row is a sub-row of its
 *  account's total row when that is significant too; otherwise it stands on its own. */
export function groupSignificant<T extends Row>(rows: T[]) {
  const totals = rows.filter((r) => r.variance_type !== "price");
  const totalCells = new Set(totals.map((r) => r.cell_id));
  const prices = rows.filter((r) => r.variance_type === "price");
  const subRows = new Map(prices.filter((p) => totalCells.has(p.cell_id)).map((p) => [p.cell_id, p]));
  const standalonePrices = prices.filter((p) => !totalCells.has(p.cell_id));
  return {
    top: rows.filter((r) => r.variance_type !== "price" || !totalCells.has(r.cell_id)),
    subRows,
    count: totals.length + standalonePrices.length,
    accounts: totals.length,
    priceEffects: standalonePrices.length,
  };
}

/** "Price effect DKK 0,37m unfavourable, partly offset by lower volume DKK 0,20m favourable.
 *  Total DKK 0,17m unfavourable." Values are profit view: positive = favourable. */
export function materialsSplit(s: {
  price_usage_variance_profit_dkk: number; volume_variance_profit_dkk: number;
  total_variance_profit_dkk: number; volume_pct_of_budget: number;
}) {
  const p = s.price_usage_variance_profit_dkk, v = s.volume_variance_profit_dkk;
  const word = (x: number) => (x >= 0 ? "favourable" : "unfavourable");
  const link = Math.sign(p) === Math.sign(v) ? "plus"
    : Math.abs(v) < Math.abs(p) ? "partly offset by" : "more than offset by";
  const vol = s.volume_pct_of_budget < 100 ? "lower" : "higher";
  return `Price effect ${millions(p)} ${word(p)}, ${link} ${vol} volume ${millions(v)} ${word(v)}. ` +
    `Total ${millions(s.total_variance_profit_dkk)} ${word(s.total_variance_profit_dkk)}.`;
}
