import { data } from "@/lib/data";

/** How good are the AI drafts? Review counts from the controller, scores from the automatic evaluation.
 *  Only totals are shown: which variances are planted events is never revealed here. */
export default function AiQuality() {
  const q = data.aiQuality;
  const drafts = data.variances.filter((v) => v.ai_comment);
  const count = (s: string | null) => drafts.filter((v) => (v.review_status ?? null) === s).length;
  const metrics: [string, string, string][] = [
    ["Approved", `${count("approved")}`, "used as written"],
    ["Edited", `${count("edited")}`, "changed by the controller"],
    ["Rejected", `${count("rejected")}`, `rewritten · ${count(null)} not reviewed yet`],
    ["Figure check", `${drafts.filter((v) => v.figure_check_passed).length}/${drafts.length}`, "every number found in the data"],
    ...(q ? [["Planted events found", `${q.planted_correct}/${q.planted_total}`,
      `right cause · noise: ${q.noise_false_claims}/${q.noise_drafted} false claims`] as [string, string, string]] : []),
  ];
  return (
    <section className="card" aria-labelledby="ai-title">
      <div className="section-head">
        <h2 id="ai-title">AI quality, all {drafts.length} drafts</h2>
        {q && <p className="muted small">{q.models.join(", ")} · prompt {q.version}</p>}
      </div>
      <div className="quality">
        {metrics.map(([label, value, note]) => (
          <div key={label} className="metric">
            <h3>{label}</h3>
            <p className="value">{value}</p>
            <p className="muted small">{note}</p>
          </div>
        ))}
      </div>
      <p className="muted small" style={{ marginTop: 12 }}>
        Planted events are causes built into the synthetic data on purpose; the score is checked automatically
        against them. Noise = significant variances with no planted cause, where the AI should not invent one.{" "}
        <a href="https://github.com/knbarka-beep/variance-cockpit/blob/main/docs/ai-layer.md#evaluation">How this is measured</a>.
      </p>
    </section>
  );
}
