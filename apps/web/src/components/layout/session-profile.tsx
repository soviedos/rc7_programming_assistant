"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import {
  fetchSession,
  getRolePath,
  logoutSession,
  switchSessionRole,
  type SessionData,
  type UserRole,
} from "@/lib/auth";

const ROLE_LABELS: Record<UserRole, string> = {
  admin: "Administrador",
  user: "Usuario",
};

export function SessionProfile() {
  const router = useRouter();
  const [session, setSession] = useState<SessionData | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadSession() {
      try {
        const currentSession = await fetchSession();
        if (isMounted) {
          setSession(currentSession);
        }
      } catch {
        if (isMounted) {
          setSession(null);
        }
      }
    }

    loadSession();

    return () => {
      isMounted = false;
    };
  }, []);

  if (!session) {
    return null;
  }

  async function handleRoleChange(nextRole: UserRole) {
    try {
      const updatedSession = await switchSessionRole(nextRole);
      setSession(updatedSession);
      router.push(getRolePath(nextRole));
    } catch {
      router.push("/");
    }
  }

  async function handleLogout() {
    try {
      await logoutSession();
    } finally {
      setSession(null);
      router.push("/");
    }
  }

  function handleProfileNavigation() {
    router.push("/profile");
  }

  return (
    <div className="session-profile">
      <div className="session-profile-copy">
        <span className="session-profile-email">{session.email}</span>
        <span className="session-profile-role">{ROLE_LABELS[session.role]}</span>
      </div>

      <div className="session-profile-actions">
        <button className="session-profile-button" type="button" onClick={handleProfileNavigation}>
          Perfil
        </button>

        <select
          className="session-role-select"
          value={session.role}
          onChange={(event) => handleRoleChange(event.target.value as UserRole)}
        >
          {session.availableRoles.map((role) => (
            <option key={role} value={role}>
              {ROLE_LABELS[role]}
            </option>
          ))}
        </select>

        <button className="session-logout-button" type="button" onClick={handleLogout}>
          Salir
        </button>
      </div>
    </div>
  );
}
