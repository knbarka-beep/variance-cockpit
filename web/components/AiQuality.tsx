import { data } from "@/lib/data";

/** How good are the AI drafts? Review counts (statuses suggested by Claude, a sample checked by Knut), scores from the automatic evaluation.
 *  Only totals are shown: which variances are planted events is never revealed here. */
export default function AiQuality() {
  const q = data.aiQuality;
  const drafts = data.variances.filter((v) => v.ai_comment);
  const byKnut = drafts.filter((v) => v.reviewed_by === "knut").length;
  const count = (s: string | null) => drafts.filter((v) => (v.review_status ?? null) === s).length;
  const metrics: [string, string, string][] = [
    ["Approved", `${count("approved")}`, "right as written"],
    ["Edited", `${count("edited")}`, "right, but misses the driver or context"],
    ["Rejected", `${count("rejected")}`, `claims something wrong${count(null) ? ` · ${count(null)} not reviewed yet` : ""}`],
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
      <p className="small" style={{ marginTop: 12 }}>
        How the drafts were reviewed: Gemini wrote them. Claude, a different model, suggested each status using written
        rules. Knut checked a pre-registered random sample of 18 and agreed with 16 ({byKnut} rows now show Knut&apos;s
        verdict). One disagreement went each way. Feb 2025, repairs: Claude approved a draft that missed an offsetting
        supplier, and Knut edited it. Sep 2026, temporary staff: Claude marked a correct draft as edited for spelling, and Knut
        approved it. 18 cases are too few to say whether Claude leans either way. The review is not blind: Claude saw the
        drafts and the ledger, and read the table of planted events only after writing its suggestions. One model grading
        another is not the same as human review.
      </p>
      <p className="muted small" style={{ marginTop: 8 }}>
        Planted events are causes built into the synthetic data on purpose; the score is checked automatically
        against them. Noise = significant variances with no planted cause, where the AI should not invent one.{" "}
        <a href="https://github.com/knbarka-beep/variance-cockpit/blob/main/docs/ai-layer.md#evaluation">How this is measured</a>.
      </p>
    </section>
  );
}
