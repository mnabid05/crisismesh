import type { DataMode } from "@/lib/types";
import { Icon } from "./icons";

const modeLabel: Record<DataMode, string> = {
  operations: "LIVE MESH",
  "live-fusion": "NEURAL LIVE",
  scenario: "SCENARIO MODE",
};

export function CommandHeader({ dataMode, incidentCount }: { dataMode: DataMode; incidentCount: number }) {
  const connected = dataMode !== "scenario";
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
        <span className={`connection-state ${connected ? "online" : "scenario"}`}><i />{modeLabel[dataMode]}</span>
        <span className="incident-counter"><Icon name="alert" />{incidentCount} signals</span>
        <button type="button" className="operator-avatar" aria-label="Operator profile">AR</button>
      </nav>
    </header>
  );
}
