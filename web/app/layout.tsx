import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ variable: "--font-inter", subsets: ["latin"] });

const site = process.env.VERCEL_PROJECT_PRODUCTION_URL ? `https://${process.env.VERCEL_PROJECT_PRODUCTION_URL}` : "http://localhost:3000";
const description = "Month-end close dashboard: budget vs actual for a fictional Danish manufacturer, with AI-drafted variance comments that are checked and reviewed. All data is synthetic.";

export const metadata: Metadata = {
  metadataBase: new URL(site),
  title: "Variance Cockpit (fictional data)",
  description,
  openGraph: { title: "Variance Cockpit", description, type: "website", images: [{ url: "/og.png", width: 1200, height: 630, alt: "Variance Cockpit dashboard, September 2026, fictional data" }] },
  twitter: { card: "summary_large_image", title: "Variance Cockpit", description, images: ["/og.png"] },
};

// Sets the saved theme before the page paints, so there is no flash of the wrong theme.
const themeScript = `try{var t=localStorage.getItem("theme");if(t)document.documentElement.dataset.theme=t}catch(e){}`;

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={inter.variable} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body>{children}</body>
    </html>
  );
}
