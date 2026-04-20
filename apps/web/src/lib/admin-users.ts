import { api } from "@/lib/api-client";

export type UserRole = "admin" | "user";

export type AdminUser = {
  id: number;
  email: string;
  displayName: string;
  role: UserRole;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
};

export type CreateAdminUserInput = {
  email: string;
  displayName: string;
  password: string;
  role: UserRole;
  isActive: boolean;
};

export type UpdateAdminUserInput = {
  displayName: string;
  role: UserRole;
  isActive: boolean;
  password?: string;
};

type AdminUserApiResponse = {
  id: number;
  email: string;
  display_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

type AdminUserListApiResponse = {
  items: AdminUserApiResponse[];
  total: number;
};

function normalizeUser(raw: AdminUserApiResponse): AdminUser {
  return {
    id: raw.id,
    email: raw.email,
    displayName: raw.display_name,
    role: raw.role,
    isActive: raw.is_active,
    createdAt: raw.created_at,
    updatedAt: raw.updated_at,
  };
}

export async function fetchAdminUsers(): Promise<AdminUser[]> {
  const raw = await api.get<AdminUserListApiResponse>(
    "/api/v1/admin/users",
    "No fue posible cargar los usuarios.",
  );
  return raw.items.map(normalizeUser);
}

export async function createAdminUser(input: CreateAdminUserInput): Promise<AdminUser> {
  const raw = await api.post<AdminUserApiResponse>(
    "/api/v1/admin/users",
    {
      email: input.email.trim().toLowerCase(),
      display_name: input.displayName.trim(),
      password: input.password,
      role: input.role,
      is_active: input.isActive,
    },
    "No fue posible crear el usuario.",
  );

  return normalizeUser(raw);
}

export async function updateAdminUser(
  userId: number,
  input: UpdateAdminUserInput,
): Promise<AdminUser> {
  const raw = await api.put<AdminUserApiResponse>(
    `/api/v1/admin/users/${userId}`,
    {
      display_name: input.displayName.trim(),
      role: input.role,
      is_active: input.isActive,
      ...(input.password ? { password: input.password } : {}),
    },
    "No fue posible actualizar el usuario.",
  );

  return normalizeUser(raw);
}

export async function deleteAdminUser(userId: number): Promise<void> {
  await api.deleteVoid(
    `/api/v1/admin/users/${userId}`,
    "No fue posible eliminar el usuario.",
  );
}
