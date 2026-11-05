import type { Metadata } from "next";
import Link from "next/link";
import { IBM_Plex_Sans, Source_Serif_4 } from "next/font/google";
import { data } from "@/lib/data";
import "./globals.css";

// Fonts are downloaded at build time and served from the site itself (no request to Google at runtime).
const serif = Source_Serif_4({ subsets: ["latin"], weight: ["400", "600"], variable: "--font-source-serif" });
const sans = IBM_Plex_Sans({ subsets: ["latin"], weight: ["400", "500", "600"], variable: "--font-plex-sans" });

const site = process.env.VERCEL_PROJECT_PRODUCTION_URL ? `https://${process.env.VERCEL_PROJECT_PRODUCTION_URL}` : "http://localhost:3000";
const description = "Month-end close dashboard: budget vs actual for a fictional Danish manufacturer, with AI-drafted variance comments that are checked and reviewed. All data is synthetic.";

export const metadata: Metadata = {
  metadataBase: new URL(site),
  title: "Variance Cockpit (fictional data)",
  description,
  openGraph: { title: "Variance Cockpit", description, type: "website", images: [{ url: "/og.png", width: 1200, height: 630, alt: "Variance Cockpit dashboard, September 2026, fictional data" }] },
  twitter: { card: "summary_large_image", title: "Variance Cockpit", description, images: ["/og.png"] },
};

// Sets the theme before the page paints: ?theme=dark|light, then the saved choice, else light (the default).
const themeScript = `(function(){try{var q=new URLSearchParams(location.search).get('theme');var t=q||localStorage.getItem('theme')||'light';document.documentElement.dataset.theme=t;}catch(e){document.documentElement.dataset.theme='light';}})();`;

const { meta } = data;

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en-GB" className={`${serif.variable} ${sans.variable}`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body>
        {children}
        <footer className="mx-auto mt-4 mb-8 grid max-w-[1200px] gap-2 border-t border-border px-4 pt-4 text-xs text-muted">
          <p>
            Significant variance: at least {meta.materiality.min_pct.toLocaleString("da-DK")} % and DKK{" "}
            {meta.materiality.min_amount_dkk.toLocaleString("da-DK")} from budget, per account, cost centre and month.
            AI comments are drafts written once and stored; this page never calls an AI model.
          </p>
          <p className="flex flex-wrap gap-x-5 gap-y-1">
            <span>{meta.company_name}: all data is synthetic</span>
            <Link href="/method/">How this works</Link>
            <a href="https://github.com/knbarka-beep/variance-cockpit">Code on GitHub</a>
          </p>
        </footer>
      </body>
    </html>
  );
}
