import { ProtectedRoute } from "@/features/auth";
import { AppHeader } from "@/components/layout/app-header";
import { AdminNav, AuditPanel } from "@/features/admin";

export default function AdminAuditPage() {
  return (
    <ProtectedRoute allowedRoles={["admin"]}>
      <div className="flex flex-col h-screen bg-bg">
        <AppHeader />
        <div className="flex-1 flex flex-col md:flex-row overflow-hidden">
          <AdminNav />
          <main className="flex-1 overflow-auto p-6">
            <AuditPanel />
          </main>
        </div>
      </div>
    </ProtectedRoute>
  );
}
