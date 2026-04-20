import { ProtectedRoute } from "@/features/auth";
import { AppHeader } from "@/components/layout/app-header";
import { SettingsPanel } from "@/features/settings";

export default function SettingsPage() {
  return (
    <ProtectedRoute allowedRoles={["admin", "user"]}>
      <div className="flex flex-col h-screen bg-bg">
        <AppHeader />
        <main className="flex-1 flex flex-col overflow-hidden">
          <SettingsPanel />
        </main>
      </div>
    </ProtectedRoute>
  );
}
