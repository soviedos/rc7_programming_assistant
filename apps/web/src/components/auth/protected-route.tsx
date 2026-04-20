"use client";

import { useRouter } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";

import { fetchSession, getRolePath, UserRole } from "@/lib/auth";

type ProtectedRouteProps = {
  allowedRoles: UserRole[];
  children: ReactNode;
};

export function ProtectedRoute({ allowedRoles, children }: ProtectedRouteProps) {
  const router = useRouter();
  const [isAuthorized, setIsAuthorized] = useState(false);

  useEffect(() => {
    let isMounted = true;

    async function validateSession() {
      try {
        const session = await fetchSession();

        if (!session) {
          router.replace("/");
          return;
        }

        if (!allowedRoles.includes(session.role)) {
          router.replace(getRolePath(session.role));
          return;
        }

        if (isMounted) {
          setIsAuthorized(true);
        }
      } catch {
        router.replace("/");
      }
    }

    validateSession();

    return () => {
      isMounted = false;
    };
  }, [allowedRoles, router]);

  if (!isAuthorized) {
    return (
      <main className="auth-loading-screen">
        <section className="auth-loading-card">
          <h2>Verificando sesión</h2>
          <p>Estamos validando tu perfil y preparando el espacio correcto.</p>
        </section>
      </main>
    );
  }

  return <>{children}</>;
}
