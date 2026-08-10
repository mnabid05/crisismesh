import Link from "next/link";

const navigation = [
  ["Predictions", "/"],
  ["Incidents", "/incidents"],
  ["Sources", "/sources"],
  ["Preparedness", "/resources"],
  ["Model card", "/model"],
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
      <a className="header-action" href="https://www.ready.gov/" target="_blank" rel="noreferrer">Get prepared ↗</a>
    </header>
  );
}
