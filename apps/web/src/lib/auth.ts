import { api } from "@/lib/api-client";

// ── Types ──────────────────────────────────────────────────────────

export type UserRole = "admin" | "user";

export type SessionData = {
  email: string;
  displayName: string;
  role: UserRole;
  availableRoles: UserRole[];
  redirectPath: string;
};

type SessionApiResponse = {
  email: string;
  display_name: string;
  role: UserRole;
  available_roles: UserRole[];
  redirect_path: string;
};

// ── Helpers ────────────────────────────────────────────────────────

function isUserRole(value: unknown): value is UserRole {
  return value === "admin" || value === "user";
}

export function getRolePath(role: UserRole): string {
  return role === "admin" ? "/admin/manuals" : "/chat";
}

function normalizeSession(payload: SessionApiResponse): SessionData {
  const availableRoles = payload.available_roles.filter(isUserRole);
  const role = availableRoles.includes(payload.role)
    ? payload.role
    : availableRoles[0] ?? "user";

  return {
    email: payload.email,
    displayName: payload.display_name,
    role,
    availableRoles: availableRoles.length > 0 ? availableRoles : [role],
    redirectPath: payload.redirect_path || getRolePath(role),
  };
}

// ── API calls ──────────────────────────────────────────────────────

export async function fetchSession(): Promise<SessionData | null> {
  const raw = await api.getMaybe<SessionApiResponse>("/api/v1/auth/me");
  return raw ? normalizeSession(raw) : null;
}

export async function loginWithPassword(
  email: string,
  password: string,
): Promise<SessionData> {
  const raw = await api.post<SessionApiResponse>(
    "/api/v1/auth/login",
    { email, password },
    "No fue posible iniciar sesión.",
  );
  return normalizeSession(raw);
}

export async function switchSessionRole(
  role: UserRole,
): Promise<SessionData> {
  const raw = await api.post<SessionApiResponse>(
    "/api/v1/auth/switch-role",
    { role },
    "No fue posible cambiar el rol activo.",
  );
  return normalizeSession(raw);
}

export async function logoutSession(): Promise<void> {
  await api.postVoid(
    "/api/v1/auth/logout",
    undefined,
    "No fue posible cerrar la sesión.",
  );
}
