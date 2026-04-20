import { ProtectedRoute } from "@/components/auth/protected-route";
import { WorkspaceHeader } from "@/components/layout/workspace-header";
import { ProfileSettingsPanel } from "@/components/profile/profile-settings-panel";
import { RobotOutline } from "@/components/shared/robot-outline";

export default function ProfilePage() {
  return (
    <ProtectedRoute allowedRoles={["admin", "user"]}>
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
          <main className="profile-page-main">
            <ProfileSettingsPanel />
          </main>
        </div>
      </div>
    </ProtectedRoute>
  );
}
