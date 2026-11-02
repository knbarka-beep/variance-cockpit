// One tooltip for every chart, in the theme colours (Recharts' default is a white box).
type Row = { label: string; value: string; strong?: boolean };
export type TooltipContent = { title: string; rows: Row[] };

type Props<T> = { active?: boolean; payload?: readonly { payload?: unknown }[]; render: (point: T) => TooltipContent };

export default function ChartTooltip<T>({ active, payload, render }: Props<T>) {
  const point = payload?.[0]?.payload as T | undefined;
  if (!active || !point) return null;
  const { title, rows } = render(point);
  return (
    <div className="tooltip">
      <p className="tooltip-title">{title}</p>
      <table>
        <tbody>
          {rows.map((r) => (
            <tr key={r.label} className={r.strong ? "strong" : undefined}><td>{r.label}</td><td className="num">{r.value}</td></tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
