import type { Metadata } from "next";
import { IBM_Plex_Sans, Source_Serif_4 } from "next/font/google";
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

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en-GB" className={`${serif.variable} ${sans.variable}`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body>{children}</body>
    </html>
  );
}
