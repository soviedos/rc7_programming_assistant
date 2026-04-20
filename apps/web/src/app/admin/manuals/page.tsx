import { ProtectedRoute } from "@/features/auth";
import { AppHeader } from "@/components/layout/app-header";
import { ManualsPanel } from "@/features/admin";

export default function AdminManualsPage() {
  return (
    <ProtectedRoute allowedRoles={["admin"]}>
      <div className="flex flex-col h-screen bg-bg">
        <AppHeader />
        <main className="flex-1 flex flex-col overflow-hidden">
          <ManualsPanel />
        </main>
      </div>
    </ProtectedRoute>
  );
}
