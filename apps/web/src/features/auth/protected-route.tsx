"use client";

import { useRouter } from "next/navigation";
import { ReactNode, useEffect } from "react";
import { Loader2 } from "lucide-react";

import { useSession } from "@/features/auth/session-provider";
import { getRolePath, type UserRole } from "@/lib/auth";

type ProtectedRouteProps = {
  allowedRoles: UserRole[];
  children: ReactNode;
};

export function ProtectedRoute({ allowedRoles, children }: ProtectedRouteProps) {
  const router = useRouter();
  const { session, isLoading } = useSession();

  useEffect(() => {
    if (isLoading) return;

    if (!session) {
      router.replace("/");
      return;
    }

    if (!allowedRoles.includes(session.role)) {
      router.replace(getRolePath(session.role));
    }
  }, [session, isLoading, allowedRoles, router]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-bg">
        <div className="flex flex-col items-center gap-3 text-muted">
          <Loader2 className="h-6 w-6 animate-spin" />
          <p className="text-sm">Verificando sesión…</p>
        </div>
      </div>
    );
  }

  if (!session || !allowedRoles.includes(session.role)) {
    return null;
  }

  return <>{children}</>;
}
