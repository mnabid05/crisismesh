import { Icon } from "./icons";

export function CommandHeader({ connected, incidentCount }: { connected: boolean; incidentCount: number }) {
  return (
    <header className="command-header">
      <a className="brand" href="#top" aria-label="CrisisMesh home">
        <span className="brand-mark"><i /><i /><i /><i /></span>
        <span><strong>CRISIS</strong>MESH</span>
      </a>
      <div className="mission-id">
        <span>OPERATIONAL VIEW</span>
        <strong>NORTH AMERICA / 01</strong>
      </div>
      <nav className="header-actions" aria-label="System status">
        <span className={`connection-state ${connected ? "online" : "scenario"}`}><i />{connected ? "LIVE MESH" : "SCENARIO MODE"}</span>
        <span className="incident-counter"><Icon name="alert" />{incidentCount} signals</span>
        <button className="operator-avatar" aria-label="Operator profile">AR</button>
      </nav>
    </header>
  );
}

