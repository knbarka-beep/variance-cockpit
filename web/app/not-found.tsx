import Link from "next/link";

export default function NotFound() {
  return (
    <main className="mx-auto max-w-[1200px] px-4 py-16">
      <h1 className="t-page">Page not found</h1>
      <p className="mt-2 text-muted">
        Variance Cockpit, Odense Demo Manufacturing ApS (fictional). All data is synthetic. <Link href="/">Back to the dashboard</Link>.
      </p>
    </main>
  );
}
