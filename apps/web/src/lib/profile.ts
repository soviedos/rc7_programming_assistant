import { api } from "@/lib/api-client";

// ── Types ──────────────────────────────────────────────────────────

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

// ── Normalizers ────────────────────────────────────────────────────

function normalizeProfile(raw: ProfileApiResponse): UserProfile {
  return {
    email: raw.email,
    displayName: raw.display_name,
    settings: {
      preferredLanguage: raw.settings.preferred_language,
    },
  };
}

// ── Validation ─────────────────────────────────────────────────────

export const PASSWORD_RULES = [
  "Al menos 8 caracteres",
  "Máximo 16 caracteres",
  "Al menos una letra mayúscula",
  "Al menos una letra minúscula",
  "Al menos un número",
  "Al menos un carácter especial",
] as const;

export function validatePasswordRules(password: string): string | null {
  if (password.length < 8) return "La nueva contraseña debe tener al menos 8 caracteres.";
  if (password.length > 16) return "La nueva contraseña debe tener como máximo 16 caracteres.";
  if (!/[A-Z]/.test(password)) return "La nueva contraseña debe incluir al menos una letra mayúscula.";
  if (!/[a-z]/.test(password)) return "La nueva contraseña debe incluir al menos una letra minúscula.";
  if (!/[0-9]/.test(password)) return "La nueva contraseña debe incluir al menos un número.";
  if (!/[^A-Za-z0-9]/.test(password)) return "La nueva contraseña debe incluir al menos un carácter especial.";
  return null;
}

// ── API calls ──────────────────────────────────────────────────────

export async function fetchProfile(): Promise<UserProfile> {
  const raw = await api.get<ProfileApiResponse>(
    "/api/v1/profile",
    "No fue posible obtener el perfil del usuario.",
  );
  return normalizeProfile(raw);
}

export async function updateProfile(
  profile: UserProfile,
): Promise<UserProfile> {
  const raw = await api.put<ProfileApiResponse>(
    "/api/v1/profile",
    {
      display_name: profile.displayName,
      settings: {
        preferred_language: profile.settings.preferredLanguage,
      },
    },
    "No fue posible actualizar el perfil.",
  );
  return normalizeProfile(raw);
}

export async function changePassword(
  currentPassword: string,
  newPassword: string,
): Promise<string> {
  const result = await api.post<ProfileActionResponse>(
    "/api/v1/profile/password",
    {
      current_password: currentPassword,
      new_password: newPassword,
    },
    "No fue posible actualizar la contraseña.",
  );
  return result.message;
}
