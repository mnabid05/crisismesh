import Link from "next/link";

export default function NotFound() {
  return <main className="loading-screen"><div className="loading-mark">404</div><h1>Sector not found</h1><p>Return to the CrisisMesh incident command view.</p><Link className="primary-button" href="/">Open command center</Link></main>;
}
