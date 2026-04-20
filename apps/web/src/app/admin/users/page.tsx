import { ProtectedRoute } from "@/features/auth";
import { AppHeader } from "@/components/layout/app-header";
import { AdminNav, UsersPanel } from "@/features/admin";

export default function AdminUsersPage() {
  return (
    <ProtectedRoute allowedRoles={["admin"]}>
      <div className="flex flex-col h-screen bg-bg">
        <AppHeader />
        <div className="flex-1 flex flex-col md:flex-row overflow-hidden">
          <AdminNav />
          <main className="flex-1 flex flex-col overflow-hidden">
            <UsersPanel />
          </main>
        </div>
      </div>
    </ProtectedRoute>
  );
}
