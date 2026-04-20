import { ProtectedRoute } from "@/features/auth";
import { AppHeader } from "@/components/layout/app-header";
import { AdminNav, RolesPanel } from "@/features/admin";

export default function AdminRolesPage() {
  return (
    <ProtectedRoute allowedRoles={["admin"]}>
      <div className="flex flex-col h-screen bg-bg">
        <AppHeader />
        <div className="flex-1 flex flex-col md:flex-row overflow-hidden">
          <AdminNav />
          <main className="flex-1 flex flex-col overflow-hidden">
            <RolesPanel />
          </main>
        </div>
      </div>
    </ProtectedRoute>
  );
}
