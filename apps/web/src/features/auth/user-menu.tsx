"use client";

import { useRouter } from "next/navigation";
import { LogOut, Settings, ChevronDown } from "lucide-react";

import { useSession } from "@/features/auth/session-provider";
import { getRolePath, type UserRole } from "@/lib/auth";

const ROLE_LABELS: Record<UserRole, string> = {
  admin: "Admin",
  user: "Usuario",
};

export function UserMenu() {
  const router = useRouter();
  const { session, switchRole, logout } = useSession();

  if (!session) return null;

  async function handleRoleChange(nextRole: UserRole) {
    try {
      await switchRole(nextRole);
      router.push(getRolePath(nextRole));
    } catch {
      router.push("/");
    }
  }

  async function handleLogout() {
    await logout();
    router.push("/");
  }

  return (
    <div className="flex items-center gap-2">
      <div className="hidden sm:flex flex-col items-end mr-1">
        <span className="text-sm font-medium text-ink truncate max-w-40">
          {session.displayName || session.email}
        </span>
        <span className="text-xs text-muted">{ROLE_LABELS[session.role]}</span>
      </div>

      {session.availableRoles.includes("admin") && session.availableRoles.length > 1 && (
        <div className="relative">
          <select
            className="appearance-none bg-surface border border-border rounded-md px-2 py-1 pr-7 text-xs text-ink cursor-pointer hover:bg-surface-hover transition-colors"
            value={session.role}
            onChange={(e) => handleRoleChange(e.target.value as UserRole)}
          >
            {session.availableRoles.map((role) => (
              <option key={role} value={role}>
                {ROLE_LABELS[role]}
              </option>
            ))}
          </select>
          <ChevronDown className="absolute right-1.5 top-1/2 -translate-y-1/2 h-3 w-3 text-muted pointer-events-none" />
        </div>
      )}

      <button
        onClick={() => router.push("/settings")}
        className="p-1.5 rounded-md text-muted hover:text-ink hover:bg-surface-hover transition-colors"
        aria-label="Configuración"
      >
        <Settings className="h-4 w-4" />
      </button>

      <button
        onClick={handleLogout}
        className="p-1.5 rounded-md text-muted hover:text-accent hover:bg-surface-hover transition-colors"
        aria-label="Cerrar sesión"
      >
        <LogOut className="h-4 w-4" />
      </button>
    </div>
  );
}
