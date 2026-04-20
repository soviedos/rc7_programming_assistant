import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ProtectedRoute } from "@/features/auth/protected-route";

const replaceMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    replace: replaceMock,
    push: vi.fn(),
  }),
}));

vi.mock("@/lib/auth", () => ({
  getRolePath: (role: "admin" | "user") => (role === "admin" ? "/admin/manuals" : "/chat"),
}));

const mockUseSession = vi.fn();
vi.mock("@/features/auth/session-provider", () => ({
  useSession: () => mockUseSession(),
}));

describe("ProtectedRoute", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders children when the session role is allowed", async () => {
    mockUseSession.mockReturnValue({
      session: {
        email: "soviedo@ucenfotec.ac.cr",
        displayName: "Sergio Oviedo",
        role: "admin",
        availableRoles: ["admin", "user"],
        redirectPath: "/admin/manuals",
      },
      isLoading: false,
    });

    render(
      <ProtectedRoute allowedRoles={["admin"]}>
        <div>Panel protegido</div>
      </ProtectedRoute>,
    );

    expect(await screen.findByText("Panel protegido")).toBeInTheDocument();
  });

  it("redirects to login when there is no active session", async () => {
    mockUseSession.mockReturnValue({
      session: null,
      isLoading: false,
    });

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
