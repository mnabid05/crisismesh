import Link from "next/link";

const navigation = [
  ["Predictions", "/"],
  ["Operations", "/operations"],
  ["Incidents", "/incidents"],
] as const;

export function SiteHeader() {
  return (
    <header className="site-header">
      <Link className="site-brand" href="/" aria-label="CrisisMesh home">
        <span className="brand-symbol" aria-hidden="true">CM</span>
        <span><strong>CrisisMesh</strong><small>Predictive response intelligence</small></span>
      </Link>
      <nav aria-label="Primary navigation">
        {navigation.map(([label, href]) => <Link href={href} key={href}>{label}</Link>)}
      </nav>
      <Link className="header-action" href="/operations">Open live map →</Link>
    </header>
  );
}
