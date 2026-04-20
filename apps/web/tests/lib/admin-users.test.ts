import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  createAdminUser,
  deleteAdminUser,
  fetchAdminUsers,
  updateAdminUser,
} from "@/lib/admin-users";

describe("admin users helpers", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("loads and normalizes users list", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify({
          items: [
            {
              id: 3,
              email: "admin@ucenfotec.ac.cr",
              display_name: "Admin",
              role: "admin",
              is_active: true,
              created_at: "2026-04-20T14:00:00Z",
              updated_at: "2026-04-20T15:00:00Z",
            },
          ],
          total: 1,
        }),
        {
          status: 200,
          headers: {
            "Content-Type": "application/json",
          },
        },
      ),
    );

    await expect(fetchAdminUsers()).resolves.toEqual([
      {
        id: 3,
        email: "admin@ucenfotec.ac.cr",
        displayName: "Admin",
        role: "admin",
        isActive: true,
        createdAt: "2026-04-20T14:00:00Z",
        updatedAt: "2026-04-20T15:00:00Z",
      },
    ]);
  });

  it("creates, updates and deletes users", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            id: 10,
            email: "user@ucenfotec.ac.cr",
            display_name: "Usuario",
            role: "user",
            is_active: true,
            created_at: "2026-04-20T14:00:00Z",
            updated_at: "2026-04-20T14:00:00Z",
          }),
          { status: 201, headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            id: 10,
            email: "user@ucenfotec.ac.cr",
            display_name: "Usuario Editado",
            role: "admin",
            is_active: true,
            created_at: "2026-04-20T14:00:00Z",
            updated_at: "2026-04-20T15:00:00Z",
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(new Response(null, { status: 204 }));

    const created = await createAdminUser({
      email: "user@ucenfotec.ac.cr",
      displayName: "Usuario",
      password: "Secure123!",
      role: "user",
      isActive: true,
    });

    expect(created.displayName).toBe("Usuario");

    const updated = await updateAdminUser(10, {
      displayName: "Usuario Editado",
      role: "admin",
      isActive: true,
      password: "Secure123!",
    });

    expect(updated.role).toBe("admin");

    await expect(deleteAdminUser(10)).resolves.toBeUndefined();
    expect(fetch).toHaveBeenCalledTimes(3);
  });
});
