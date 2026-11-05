import { data } from "@/lib/data";
import { Card, CardHeader } from "./kit/Card";
import { InfoTip } from "./kit/InfoTip";

const MEASURED = "https://github.com/knbarka-beep/variance-cockpit/blob/main/docs/ai-layer.md#evaluation";

/** How good are the AI drafts? Review counts (statuses suggested by Claude, a sample checked by Knut), scores from the automatic evaluation.
 *  Only totals are shown: which variances are planted events is never revealed here.
 *  The definitions and the review story sit in (i) popovers; the counts and "16 of 18" stay on the card. */
export default function AiQuality() {
  const q = data.aiQuality;
  const drafts = data.variances.filter((v) => v.ai_comment);
  const byKnut = drafts.filter((v) => v.reviewed_by === "knut").length;
  const count = (s: string | null) => drafts.filter((v) => (v.review_status ?? null) === s).length;
  const metrics: [string, string, string][] = [
    ["Approved", `${count("approved")}`, "right as written"],
    ["Edited", `${count("edited")}`, "right, but misses the driver or context"],
    ["Rejected", `${count("rejected")}`, "claims something wrong"],
    ["Figure check", `${drafts.filter((v) => v.figure_check_passed).length}/${drafts.length}`, "every number found in the data"],
    ...(q ? [["Planted events found", `${q.planted_correct}/${q.planted_total}`,
      `right cause · noise: ${q.noise_false_claims}/${q.noise_drafted} false claims`] as [string, string, string]] : []),
  ];
  return (
    <Card aria-labelledby="ai-title">
      <CardHeader id="ai-title" title={`AI quality, all ${drafts.length} drafts`}
        aside={q ? `${q.models.join(", ")} · prompt ${q.version}` : undefined}
        info={<>
          <ul>{metrics.map(([l, , note]) => <li key={l}><b>{l}</b>: {note}</li>)}</ul>
          <p>Planted events are causes built into the synthetic data on purpose; the score is checked automatically
            against them. Noise = significant variances with no planted cause, where the AI should not invent one.{" "}
            <a href={MEASURED}>How this is measured</a>.</p>
        </>} />
      <dl className="grid grid-cols-2 gap-x-6 gap-y-5 sm:grid-cols-3 lg:grid-cols-5">
        {metrics.map(([l, value]) => (
          <div key={l} className="min-w-0">
            <dt className="t-label">{l}</dt>
            <dd className="mt-1 text-[1.4rem] leading-tight font-semibold">{value}</dd>
          </div>
        ))}
      </dl>
      <div className="t-small mt-5 flex flex-wrap items-center gap-x-1.5 border-t border-border pt-3 text-muted">
        <span>
          Gemini wrote the drafts and Claude suggested each status. Knut checked a random sample:{" "}
          <b className="font-semibold text-text">agreed with 16 of 18</b>.
          {count(null) > 0 && ` ${count(null)} not reviewed yet.`}
        </span>
        <InfoTip label="how the drafts were reviewed" align="right">
          <p>How the drafts were reviewed: Gemini wrote them. Claude, a different model, suggested each status using written
            rules. Knut checked a pre-registered random sample of 18 and agreed with 16 ({byKnut} rows now show Knut&apos;s
            verdict). One disagreement went each way.</p>
          <p>Feb 2025, repairs: Claude approved a draft that missed an offsetting supplier, and Knut edited it. Sep 2026,
            temporary staff: Claude marked a correct draft as edited for spelling, and Knut approved it.</p>
          <p>18 cases are too few to say whether Claude leans either way. The review is not blind: Claude saw the drafts and
            the ledger, and read the table of planted events only after writing its suggestions. One model grading another is
            not the same as human review.</p>
        </InfoTip>
      </div>
    </Card>
  );
}
