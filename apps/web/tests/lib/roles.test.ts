import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  createRolePermission,
  deleteRolePermission,
  fetchRolePermissions,
  updateRolePermission,
} from "@/lib/roles";

describe("roles helpers", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("loads and normalizes role permissions matrix", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify({
          items: [
            {
              id: 1,
              key: "manuals",
              name: "Manuales",
              description: "Ver, subir y gestionar la base documental.",
              admin: true,
              user: false,
            },
            {
              id: 2,
              key: "chat",
              name: "Chat",
              description: "Usar el asistente para consultas técnicas.",
              admin: true,
              user: true,
            },
          ],
        }),
        {
          status: 200,
          headers: {
            "Content-Type": "application/json",
          },
        },
      ),
    );

    await expect(fetchRolePermissions()).resolves.toEqual([
      {
        id: 1,
        key: "manuals",
        name: "Manuales",
        description: "Ver, subir y gestionar la base documental.",
        admin: true,
        user: false,
      },
      {
        id: 2,
        key: "chat",
        name: "Chat",
        description: "Usar el asistente para consultas técnicas.",
        admin: true,
        user: true,
      },
    ]);
  });

  it("creates, updates and deletes role permissions", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            id: 10,
            key: "reports",
            name: "Reportes",
            description: "Acceso a reportes",
            admin: true,
            user: false,
          }),
          { status: 201, headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            id: 10,
            key: "reports",
            name: "Reportes y metricas",
            description: "Acceso a reportes y metricas",
            admin: true,
            user: true,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(new Response(null, { status: 204 }));

    const created = await createRolePermission({
      key: "reports",
      name: "Reportes",
      description: "Acceso a reportes",
      admin: true,
      user: false,
    });
    expect(created.id).toBe(10);

    const updated = await updateRolePermission(10, {
      name: "Reportes y metricas",
      description: "Acceso a reportes y metricas",
      admin: true,
      user: true,
    });
    expect(updated.user).toBe(true);

    await expect(deleteRolePermission(10)).resolves.toBeUndefined();
    expect(fetch).toHaveBeenCalledTimes(3);
  });
});
