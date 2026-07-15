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

type RolePermissionListApiResponse = {
  items: RolePermission[];
};

export async function fetchRolePermissions(): Promise<RolePermission[]> {
  const raw = await api.get<RolePermissionListApiResponse>(
    "/api/v1/admin/roles/permissions",
    "No fue posible cargar la matriz de permisos.",
  );
  return raw.items;
}

export async function createRolePermission(
  input: CreateRolePermissionInput,
): Promise<RolePermission> {
  const raw = await api.post<RolePermission>(
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
  return raw;
}

export async function updateRolePermission(
  permissionId: number,
  input: UpdateRolePermissionInput,
): Promise<RolePermission> {
  const raw = await api.put<RolePermission>(
    `/api/v1/admin/roles/permissions/${permissionId}`,
    {
      name: input.name.trim(),
      description: input.description.trim(),
      admin: input.admin,
      user: input.user,
    },
    "No fue posible actualizar el permiso.",
  );
  return raw;
}

export async function deleteRolePermission(permissionId: number): Promise<void> {
  await api.deleteVoid(
    `/api/v1/admin/roles/permissions/${permissionId}`,
    "No fue posible eliminar el permiso.",
  );
}
