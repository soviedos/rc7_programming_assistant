"use client";

import {
  createContext,
  ReactNode,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";

import {
  fetchSession,
  logoutSession,
  switchSessionRole,
  type SessionData,
  type UserRole,
} from "@/lib/auth";

type SessionState = {
  session: SessionData | null;
  isLoading: boolean;
  switchRole: (role: UserRole) => Promise<SessionData>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
};

const SessionContext = createContext<SessionState | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<SessionData | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const loadSession = useCallback(async () => {
    try {
      const data = await fetchSession();
      setSession(data);
    } catch {
      setSession(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSession();
  }, [loadSession]);

  const switchRole = useCallback(async (role: UserRole) => {
    const updated = await switchSessionRole(role);
    setSession(updated);
    return updated;
  }, []);

  const logout = useCallback(async () => {
    try {
      await logoutSession();
    } finally {
      setSession(null);
    }
  }, []);

  return (
    <SessionContext.Provider
      value={{ session, isLoading, switchRole, logout, refresh: loadSession }}
    >
      {children}
    </SessionContext.Provider>
  );
}

export function useSession(): SessionState {
  const ctx = useContext(SessionContext);
  if (!ctx) {
    throw new Error("useSession must be used within a SessionProvider");
  }
  return ctx;
}
