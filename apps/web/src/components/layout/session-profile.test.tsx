import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SessionProfile } from "@/components/layout/session-profile";
import { fetchSession, logoutSession, switchSessionRole } from "@/lib/auth";

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    replace: vi.fn(),
    push: pushMock,
  }),
}));

vi.mock("@/lib/auth", () => ({
  fetchSession: vi.fn(),
  getRolePath: (role: "admin" | "user") => (role === "admin" ? "/admin" : "/app"),
  logoutSession: vi.fn(),
  switchSessionRole: vi.fn(),
}));

describe("SessionProfile", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(fetchSession).mockResolvedValue({
      email: "soviedo@ucenfotec.ac.cr",
      displayName: "Sergio Oviedo",
      role: "admin",
      availableRoles: ["admin", "user"],
      redirectPath: "/admin",
    });
  });

  it("renders the current session identity", async () => {
    render(<SessionProfile />);

    expect(await screen.findByText("soviedo@ucenfotec.ac.cr")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Administrador")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Perfil" })).toBeInTheDocument();
  });

  it("switches role and navigates to the matching page", async () => {
    const user = userEvent.setup();
    vi.mocked(switchSessionRole).mockResolvedValue({
      email: "soviedo@ucenfotec.ac.cr",
      displayName: "Sergio Oviedo",
      role: "user",
      availableRoles: ["admin", "user"],
      redirectPath: "/app",
    });

    render(<SessionProfile />);

    const select = await screen.findByDisplayValue("Administrador");
    await user.selectOptions(select, "user");

    await waitFor(() => {
      expect(switchSessionRole).toHaveBeenCalledWith("user");
      expect(pushMock).toHaveBeenCalledWith("/app");
    });
  });

  it("logs out and returns to the login page", async () => {
    const user = userEvent.setup();
    vi.mocked(logoutSession).mockResolvedValue();

    render(<SessionProfile />);

    await user.click(await screen.findByRole("button", { name: "Salir" }));

    await waitFor(() => {
      expect(logoutSession).toHaveBeenCalled();
      expect(pushMock).toHaveBeenCalledWith("/");
    });
  });

  it("navigates to profile settings from the header", async () => {
    const user = userEvent.setup();

    render(<SessionProfile />);

    await user.click(await screen.findByRole("button", { name: "Perfil" }));

    await waitFor(() => {
      expect(pushMock).toHaveBeenCalledWith("/profile");
    });
  });
});
