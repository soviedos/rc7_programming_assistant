import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ProtectedRoute } from "@/components/auth/protected-route";
import { fetchSession } from "@/lib/auth";

const replaceMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    replace: replaceMock,
    push: vi.fn(),
  }),
}));

vi.mock("@/lib/auth", () => ({
  fetchSession: vi.fn(),
  getRolePath: (role: "admin" | "user") => (role === "admin" ? "/admin" : "/app"),
}));

describe("ProtectedRoute", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders children when the session role is allowed", async () => {
    vi.mocked(fetchSession).mockResolvedValue({
      email: "soviedo@ucenfotec.ac.cr",
      displayName: "Sergio Oviedo",
      role: "admin",
      availableRoles: ["admin", "user"],
      redirectPath: "/admin",
    });

    render(
      <ProtectedRoute allowedRoles={["admin"]}>
        <div>Panel protegido</div>
      </ProtectedRoute>,
    );

    expect(await screen.findByText("Panel protegido")).toBeInTheDocument();
  });

  it("redirects to login when there is no active session", async () => {
    vi.mocked(fetchSession).mockResolvedValue(null);

    render(
      <ProtectedRoute allowedRoles={["admin"]}>
        <div>Panel protegido</div>
      </ProtectedRoute>,
    );

    await waitFor(() => {
      expect(replaceMock).toHaveBeenCalledWith("/");
    });
  });
});
