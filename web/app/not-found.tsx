import Link from "next/link";

export default function NotFound() {
  return (
    <div className="page">
      <h1>Page not found</h1>
      <p className="muted">
        Variance Cockpit, Odense Demo Manufacturing ApS (fictional). All data is synthetic. <Link href="/">Back to the dashboard</Link>.
      </p>
    </div>
  );
}
