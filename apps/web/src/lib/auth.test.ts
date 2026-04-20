import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  fetchSession,
  getRolePath,
  loginWithPassword,
  normalizeSession,
} from "@/lib/auth";

describe("auth helpers", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("maps valid roles and redirect paths correctly", () => {
    const session = normalizeSession({
      email: "soviedo@ucenfotec.ac.cr",
      display_name: "Sergio Oviedo",
      role: "admin",
      available_roles: ["admin", "user"],
      redirect_path: "/admin",
    });

    expect(session.email).toBe("soviedo@ucenfotec.ac.cr");
    expect(session.displayName).toBe("Sergio Oviedo");
    expect(session.role).toBe("admin");
    expect(session.availableRoles).toEqual(["admin", "user"]);
    expect(session.redirectPath).toBe("/admin");
    expect(getRolePath("user")).toBe("/app");
  });

  it("returns null when the session endpoint answers 401", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(null, {
        status: 401,
      }),
    );

    await expect(fetchSession()).resolves.toBeNull();
  });

  it("normalizes validation errors returned by the API", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: [
            { msg: "Field required" },
            { msg: "String should have at least 6 characters" },
          ],
        }),
        {
          status: 422,
          headers: {
            "Content-Type": "application/json",
          },
        },
      ),
    );

    await expect(loginWithPassword("", "")).rejects.toThrow(
      "Field required String should have at least 6 characters",
    );
  });
});
