import type { Metadata } from "next";
import { SiteHeader } from "@/components/site-header";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "CrisisMesh — Predictive disaster response", template: "%s · CrisisMesh" },
  description: "Multi-source disaster intelligence with transparent 6, 24, and 72-hour escalation estimates.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body><SiteHeader />{children}<footer className="site-footer"><strong>CrisisMesh</strong><span>Experimental decision support · Always follow official instructions.</span><a href="https://github.com/mnabid05/crisismesh" target="_blank" rel="noreferrer">Open source ↗</a></footer></body>
    </html>
  );
}
