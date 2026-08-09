"use client";

export default function ErrorPage({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return <main className="loading-screen"><div className="loading-mark alert">!</div><h1>Command view unavailable</h1><p>The incident feed could not be rendered.</p><button className="primary-button" onClick={reset}>Retry connection</button></main>;
}

