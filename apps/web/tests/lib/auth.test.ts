import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  fetchSession,
  getRolePath,
  loginWithPassword,
} from "@/lib/auth";

describe("auth helpers", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("maps valid roles to correct redirect paths", () => {
    expect(getRolePath("admin")).toBe("/admin/manuals");
    expect(getRolePath("user")).toBe("/chat");
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
