import type { Metadata } from "next";
import Link from "next/link";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { PageHeader } from "@/components/kit/PageHeader";
import { ThemeToggle } from "@/components/kit/ThemeToggle";
import { data } from "@/lib/data";

export const metadata: Metadata = { title: "How this works: Variance Cockpit (fictional data)" };

// Rendered at build time from lib/method.md, a copy of docs/method-draft.md (scripts/prepare-data.mjs).
// The text uses only a small part of Markdown: # and ## headings, paragraphs, "- " and "1. " lists, **bold** and `code`.
// ponytail: tiny renderer for that subset; switch to a Markdown library if the doc ever needs tables or links.
const md = readFileSync(join(process.cwd(), "lib", "method.md"), "utf8");
const slug = (t: string) => t.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

function inline(text: string) {
  return text.split(/(\*\*[^*]+\*\*|`[^`]+`)/).map((part, i) =>
    part.startsWith("**") ? <b key={i}>{part.slice(2, -2)}</b>
      : part.startsWith("`") ? <code key={i}>{part.slice(1, -1)}</code>
        : part);
}

function block(text: string, i: number) {
  const lines = text.split("\n");
  if (text.startsWith("# ")) return <h1 key={i}>{inline(text.slice(2))}</h1>;
  if (text.startsWith("## ")) return <h2 key={i} id={slug(text.slice(3))}>{inline(text.slice(3))}</h2>;
  if (lines.every((l) => l.startsWith("- "))) return <ul key={i}>{lines.map((l, j) => <li key={j}>{inline(l.slice(2))}</li>)}</ul>;
  if (lines.every((l) => /^\d+\. /.test(l))) return <ol key={i}>{lines.map((l, j) => <li key={j}>{inline(l.replace(/^\d+\. /, ""))}</li>)}</ol>;
  return <p key={i}>{inline(lines.join(" "))}</p>;
}

export default function Method() {
  return (
    <>
      <PageHeader title="Variance Cockpit" suffix={`· ${data.meta.company_name}`}>
        <Link href="/" className="btn">Dashboard</Link>
        <ThemeToggle />
      </PageHeader>
      <main className="mx-auto max-w-[1200px] px-4 pt-6 pb-4">
        <p className="t-small text-muted">All data on this site is synthetic.</p>
        <div className="method">{md.trim().split(/\n\s*\n/).map(block)}</div>
      </main>
    </>
  );
}
