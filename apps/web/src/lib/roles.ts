import { api } from "@/lib/api-client";

export type RolePermission = {
  id: number;
  key: string;
  name: string;
  description: string;
  admin: boolean;
  user: boolean;
};

export type CreateRolePermissionInput = {
  key: string;
  name: string;
  description: string;
  admin: boolean;
  user: boolean;
};

export type UpdateRolePermissionInput = {
  name: string;
  description: string;
  admin: boolean;
  user: boolean;
};

type RolePermissionApiResponse = {
  id: number;
  key: string;
  name: string;
  description: string;
  admin: boolean;
  user: boolean;
};

type RolePermissionListApiResponse = {
  items: RolePermissionApiResponse[];
};

function normalizePermission(raw: RolePermissionApiResponse): RolePermission {
  return {
    id: raw.id,
    key: raw.key,
    name: raw.name,
    description: raw.description,
    admin: raw.admin,
    user: raw.user,
  };
}

export async function fetchRolePermissions(): Promise<RolePermission[]> {
  const raw = await api.get<RolePermissionListApiResponse>(
    "/api/v1/admin/roles/permissions",
    "No fue posible cargar la matriz de permisos.",
  );
  return raw.items.map(normalizePermission);
}

export async function createRolePermission(
  input: CreateRolePermissionInput,
): Promise<RolePermission> {
  const raw = await api.post<RolePermissionApiResponse>(
    "/api/v1/admin/roles/permissions",
    {
      key: input.key.trim().toLowerCase(),
      name: input.name.trim(),
      description: input.description.trim(),
      admin: input.admin,
      user: input.user,
    },
    "No fue posible crear el permiso.",
  );
  return normalizePermission(raw);
}

export async function updateRolePermission(
  permissionId: number,
  input: UpdateRolePermissionInput,
): Promise<RolePermission> {
  const raw = await api.put<RolePermissionApiResponse>(
    `/api/v1/admin/roles/permissions/${permissionId}`,
    {
      name: input.name.trim(),
      description: input.description.trim(),
      admin: input.admin,
      user: input.user,
    },
    "No fue posible actualizar el permiso.",
  );
  return normalizePermission(raw);
}

export async function deleteRolePermission(permissionId: number): Promise<void> {
  await api.deleteVoid(
    `/api/v1/admin/roles/permissions/${permissionId}`,
    "No fue posible eliminar el permiso.",
  );
}
