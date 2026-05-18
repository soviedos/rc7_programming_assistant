import { api } from "@/lib/api-client";

export type SystemSetting = {
  id: number;
  key: string;
  value: string;
  description: string;
  updatedAt: string;
};

type SettingApiResponse = {
  id: number;
  key: string;
  value: string;
  description: string;
  updated_at: string;
};

type SettingsListApiResponse = {
  items: SettingApiResponse[];
};

function normalizeSetting(raw: SettingApiResponse): SystemSetting {
  return {
    id: raw.id,
    key: raw.key,
    value: raw.value,
    description: raw.description,
    updatedAt: raw.updated_at,
  };
}

export async function fetchSettings(): Promise<SystemSetting[]> {
  const raw = await api.get<SettingsListApiResponse>(
    "/api/v1/admin/settings",
    "No fue posible cargar la configuración.",
  );
  return raw.items.map(normalizeSetting);
}

export async function updateSetting(
  key: string,
  value: string,
): Promise<SystemSetting> {
  const raw = await api.put<SettingApiResponse>(
    `/api/v1/admin/settings/${key}`,
    { value },
    `No fue posible guardar el parámetro '${key}'.`,
  );
  return normalizeSetting(raw);
}

export async function resetSettings(): Promise<SystemSetting[]> {
  const raw = await api.post<SettingsListApiResponse>(
    "/api/v1/admin/settings/reset",
    {},
    "No fue posible restablecer la configuración.",
  );
  return raw.items.map(normalizeSetting);
}
