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

type ApiValidationDetail = {
  loc?: Array<string | number>;
  msg?: string;
  type?: string;
};

type ApiErrorResponse = {
  detail?: string | ApiValidationDetail[];
};

function isUserRole(value: unknown): value is UserRole {
  return value === "admin" || value === "user";
}

export function getRolePath(role: UserRole): string {
  return role === "admin" ? "/admin" : "/app";
}

export function getApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
}

export function normalizeSession(payload: SessionApiResponse): SessionData {
  const availableRoles = payload.available_roles.filter(isUserRole);
  const role = availableRoles.includes(payload.role) ? payload.role : availableRoles[0] ?? "user";

  return {
    email: payload.email,
    displayName: payload.display_name,
    role,
    availableRoles: availableRoles.length > 0 ? availableRoles : [role],
    redirectPath: payload.redirect_path || getRolePath(role),
  };
}

async function parseResponse<T>(response: Response): Promise<T> {
  return (await response.json()) as T;
}

function normalizeApiErrorMessage(
  detail: ApiErrorResponse["detail"],
  fallback: string,
): string {
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((entry) => entry.msg?.trim())
      .filter((message): message is string => Boolean(message));

    if (messages.length > 0) {
      return messages.join(" ");
    }
  }

  return fallback;
}

export async function fetchSession(): Promise<SessionData | null> {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/auth/me`, {
    credentials: "include",
  });

  if (response.status === 401) {
    return null;
  }

  if (!response.ok) {
    const payload = await parseResponse<ApiErrorResponse>(response);
    throw new Error(
      normalizeApiErrorMessage(payload.detail, "No se pudo obtener la sesión actual."),
    );
  }

  const payload = await parseResponse<SessionApiResponse>(response);
  return normalizeSession(payload);
}

export async function loginWithPassword(
  email: string,
  password: string,
): Promise<SessionData> {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/auth/login`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      email,
      password,
    }),
  });

  const payload = await parseResponse<SessionApiResponse | ApiErrorResponse>(response);
  if (!response.ok) {
    throw new Error(
      normalizeApiErrorMessage(
        "detail" in payload ? payload.detail : undefined,
        "No fue posible iniciar sesión.",
      ),
    );
  }

  return normalizeSession(payload as SessionApiResponse);
}

export async function switchSessionRole(role: UserRole): Promise<SessionData> {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/auth/switch-role`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ role }),
  });

  const payload = await parseResponse<SessionApiResponse | ApiErrorResponse>(response);
  if (!response.ok) {
    throw new Error(
      normalizeApiErrorMessage(
        "detail" in payload ? payload.detail : undefined,
        "No fue posible cambiar el rol activo.",
      ),
    );
  }

  return normalizeSession(payload as SessionApiResponse);
}

export async function logoutSession(): Promise<void> {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/auth/logout`, {
    method: "POST",
    credentials: "include",
  });

  if (!response.ok) {
    const payload = await parseResponse<ApiErrorResponse>(response);
    throw new Error(
      normalizeApiErrorMessage(payload.detail, "No fue posible cerrar la sesión."),
    );
  }
}
