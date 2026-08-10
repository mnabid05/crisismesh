import type { Metadata } from "next";
import Link from "next/link";
import { SiteHeader } from "@/components/site-header";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "CrisisMesh — Predictive disaster response", template: "%s · CrisisMesh" },
  description: "Multi-source disaster intelligence with transparent 6, 24, and 72-hour escalation estimates.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body><SiteHeader />{children}<footer className="site-footer"><div className="footer-brand"><strong>CrisisMesh</strong><p>Predictive disaster response and collaborative operations.</p></div><div className="footer-links"><section><span>Platform</span><Link href="/">Predictions</Link><Link href="/operations">Operations map</Link><Link href="/incidents">Active incidents</Link></section><section><span>Resources</span><Link href="/sources">Data sources</Link><Link href="/resources">Preparedness</Link><Link href="/model">Model card</Link></section><section><span>Trust & project</span><Link href="/model">Safety disclosure</Link><a href="https://github.com/mnabid05/crisismesh/blob/main/LICENSE" target="_blank" rel="noreferrer">License ↗</a><a href="https://github.com/mnabid05/crisismesh" target="_blank" rel="noreferrer">GitHub ↗</a></section></div><div className="footer-legal"><span>Experimental decision support. Not an official warning or evacuation authority.</span><span>© 2026 CrisisMesh</span></div></footer></body>
    </html>
  );
}
