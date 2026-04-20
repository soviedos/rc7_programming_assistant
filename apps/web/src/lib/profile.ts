import { getApiBaseUrl } from "@/lib/auth";

export type PreferredLanguage = "es" | "en";

export type UserProfileSettings = {
  preferredLanguage: PreferredLanguage;
};

export type UserProfile = {
  email: string;
  displayName: string;
  settings: UserProfileSettings;
};

type ProfileApiResponse = {
  email: string;
  display_name: string;
  settings: {
    preferred_language: PreferredLanguage;
  };
};

type ProfileActionResponse = {
  success: boolean;
  message: string;
};

type ApiValidationDetail = {
  msg?: string;
};

type ApiErrorResponse = {
  detail?: string | ApiValidationDetail[];
};

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

async function parseResponse<T>(response: Response): Promise<T> {
  return (await response.json()) as T;
}

function normalizeProfile(payload: ProfileApiResponse): UserProfile {
  return {
    email: payload.email,
    displayName: payload.display_name,
    settings: {
      preferredLanguage: payload.settings.preferred_language,
    },
  };
}

export const PASSWORD_RULES = [
  "Al menos 8 caracteres",
  "Máximo 16 caracteres",
  "Al menos una letra mayúscula",
  "Al menos una letra minúscula",
  "Al menos un número",
  "Al menos un carácter especial",
] as const;

export function validatePasswordRules(password: string): string | null {
  if (password.length < 8) {
    return "La nueva contraseña debe tener al menos 8 caracteres.";
  }

  if (password.length > 16) {
    return "La nueva contraseña debe tener como máximo 16 caracteres.";
  }

  if (!/[A-Z]/.test(password)) {
    return "La nueva contraseña debe incluir al menos una letra mayúscula.";
  }

  if (!/[a-z]/.test(password)) {
    return "La nueva contraseña debe incluir al menos una letra minúscula.";
  }

  if (!/[0-9]/.test(password)) {
    return "La nueva contraseña debe incluir al menos un número.";
  }

  if (!/[^A-Za-z0-9]/.test(password)) {
    return "La nueva contraseña debe incluir al menos un carácter especial.";
  }

  return null;
}

export async function fetchProfile(): Promise<UserProfile> {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/profile`, {
    credentials: "include",
  });

  const payload = await parseResponse<ProfileApiResponse | ApiErrorResponse>(response);
  if (!response.ok) {
    throw new Error(
      normalizeApiErrorMessage(
        "detail" in payload ? payload.detail : undefined,
        "No fue posible obtener el perfil del usuario.",
      ),
    );
  }

  return normalizeProfile(payload as ProfileApiResponse);
}

export async function updateProfile(profile: UserProfile): Promise<UserProfile> {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/profile`, {
    method: "PUT",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      display_name: profile.displayName,
      settings: {
        preferred_language: profile.settings.preferredLanguage,
      },
    }),
  });

  const payload = await parseResponse<ProfileApiResponse | ApiErrorResponse>(response);
  if (!response.ok) {
    throw new Error(
      normalizeApiErrorMessage(
        "detail" in payload ? payload.detail : undefined,
        "No fue posible actualizar el perfil.",
      ),
    );
  }

  return normalizeProfile(payload as ProfileApiResponse);
}

export async function changePassword(
  currentPassword: string,
  newPassword: string,
): Promise<string> {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/profile/password`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });

  const payload = await parseResponse<ProfileActionResponse | ApiErrorResponse>(response);
  if (!response.ok) {
    throw new Error(
      normalizeApiErrorMessage(
        "detail" in payload ? payload.detail : undefined,
        "No fue posible actualizar la contraseña.",
      ),
    );
  }

  return (payload as ProfileActionResponse).message;
}
