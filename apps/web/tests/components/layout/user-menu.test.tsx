import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { UserMenu } from "@/features/auth/user-menu";

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    replace: vi.fn(),
    push: pushMock,
  }),
}));

vi.mock("@/lib/auth", () => ({
  getRolePath: (role: "admin" | "user") => (role === "admin" ? "/admin/manuals" : "/chat"),
}));

const mockSwitchRole = vi.fn();
const mockLogout = vi.fn();

vi.mock("@/features/auth/session-provider", () => ({
  useSession: () => ({
    session: {
      email: "soviedo@ucenfotec.ac.cr",
      displayName: "Sergio Oviedo",
      role: "admin",
      availableRoles: ["admin", "user"],
      redirectPath: "/admin/manuals",
    },
    isLoading: false,
    switchRole: mockSwitchRole,
    logout: mockLogout,
  }),
}));

describe("UserMenu", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the current session identity", () => {
    render(<UserMenu />);

    expect(screen.getByText("Sergio Oviedo")).toBeInTheDocument();
    expect(screen.getAllByText("Admin").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByRole("button", { name: "Configuración" })).toBeInTheDocument();
  });

  it("navigates to settings when settings button is clicked", async () => {
    const user = userEvent.setup();
    render(<UserMenu />);

    await user.click(screen.getByRole("button", { name: "Configuración" }));
    expect(pushMock).toHaveBeenCalledWith("/settings");
  });

  it("logs out and redirects to login", async () => {
    const user = userEvent.setup();
    mockLogout.mockResolvedValue(undefined);

    render(<UserMenu />);

    await user.click(screen.getByRole("button", { name: "Cerrar sesión" }));

    await waitFor(() => {
      expect(mockLogout).toHaveBeenCalled();
      expect(pushMock).toHaveBeenCalledWith("/");
    });
  });
});
