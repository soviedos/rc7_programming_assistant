import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { changePassword, fetchProfile, updateProfile } from "@/lib/profile";

describe("profile helpers", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("loads and normalizes the profile payload", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify({
          email: "soviedo@ucenfotec.ac.cr",
          display_name: "Sergio Oviedo",
          settings: {
            preferred_language: "es",
          },
        }),
        {
          status: 200,
          headers: {
            "Content-Type": "application/json",
          },
        },
      ),
    );

    await expect(fetchProfile()).resolves.toEqual({
      email: "soviedo@ucenfotec.ac.cr",
      displayName: "Sergio Oviedo",
      settings: {
        preferredLanguage: "es",
      },
    });
  });

  it("propagates validation messages when updating the profile fails", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: [{ msg: "String should have at least 2 characters" }],
        }),
        {
          status: 422,
          headers: {
            "Content-Type": "application/json",
          },
        },
      ),
    );

    await expect(
      updateProfile({
        email: "soviedo@ucenfotec.ac.cr",
        displayName: "A",
        settings: {
          preferredLanguage: "es",
        },
      }),
    ).rejects.toThrow("String should have at least 2 characters");
  });

  it("returns the success message when the password is changed", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify({
          success: true,
          message: "La contraseña se actualizó correctamente.",
        }),
        {
          status: 200,
          headers: {
            "Content-Type": "application/json",
          },
        },
      ),
    );

    await expect(changePassword("1234ABC", "ZXCV1234")).resolves.toBe(
      "La contraseña se actualizó correctamente.",
    );
  });
});
