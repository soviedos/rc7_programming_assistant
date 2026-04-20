import type { ReactNode } from "react";

import { WorkspaceHeader } from "@/components/layout/workspace-header";
import { RobotOutline } from "@/components/shared/robot-outline";

type AppShellProps = {
  leftSidebar: ReactNode;
  main: ReactNode;
  rightSidebar: ReactNode;
};

export function AppShell({ leftSidebar, main, rightSidebar }: AppShellProps) {
  return (
    <div className="workspace-screen">
      <div className="workspace-backdrop" />
      <div className="workspace-grid-floor" />
      <div className="workspace-dots workspace-dots-right" />
      <div className="workspace-dots workspace-dots-center" />

      <div className="workspace-illustration workspace-illustration-left">
        <RobotOutline className="robot-outline" />
      </div>

      <div className="app-frame">
        <WorkspaceHeader />
        <main className="app-shell">
          <aside className="sidebar sidebar-left">{leftSidebar}</aside>
          <section className="app-main">{main}</section>
          <aside className="sidebar sidebar-right">{rightSidebar}</aside>
        </main>
      </div>
    </div>
  );
}
