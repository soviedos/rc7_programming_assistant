import { SessionProfile } from "@/components/layout/session-profile";

export function WorkspaceHeader() {
  return (
    <header className="topbar">
      <div className="workspace-header-main">
        <div className="topbar-brand">
          <p className="topbar-kicker">RobLab | Universidad CENFOTEC</p>
          <h1 className="topbar-title">Asistente de Programación DENSO RC7</h1>
        </div>
      </div>

      <div className="topbar-meta">
        <SessionProfile />
      </div>
    </header>
  );
}
