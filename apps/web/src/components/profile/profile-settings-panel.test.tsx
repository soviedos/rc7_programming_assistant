import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ProfileSettingsPanel } from "@/components/profile/profile-settings-panel";
import { changePassword, fetchProfile, updateProfile } from "@/lib/profile";
import { fetchSession } from "@/lib/auth";

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: pushMock,
    replace: vi.fn(),
  }),
}));

vi.mock("@/lib/auth", () => ({
  fetchSession: vi.fn(),
}));

vi.mock("@/lib/profile", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/profile")>();

  return {
    ...actual,
    changePassword: vi.fn(),
    fetchProfile: vi.fn(),
    updateProfile: vi.fn(),
  };
});

describe("ProfileSettingsPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    pushMock.mockReset();
    vi.mocked(fetchSession).mockResolvedValue({
      email: "soviedo@ucenfotec.ac.cr",
      displayName: "Sergio Oviedo",
      role: "admin",
      availableRoles: ["admin", "user"],
      redirectPath: "/admin",
    });
    vi.mocked(fetchProfile).mockResolvedValue({
      email: "soviedo@ucenfotec.ac.cr",
      displayName: "Sergio Oviedo",
      settings: {
        preferredLanguage: "es",
      },
    });
  });

  it("loads and displays the current profile", async () => {
    render(<ProfileSettingsPanel />);

    expect(await screen.findByDisplayValue("Sergio Oviedo")).toBeInTheDocument();
    expect(screen.getByDisplayValue("soviedo@ucenfotec.ac.cr")).toBeInTheDocument();
  });

  it("updates profile preferences successfully", async () => {
    const user = userEvent.setup();
    vi.mocked(updateProfile).mockResolvedValue({
      email: "soviedo@ucenfotec.ac.cr",
      displayName: "Ing. Sergio Oviedo",
      settings: {
        preferredLanguage: "en",
      },
    });

    render(<ProfileSettingsPanel />);

    const displayNameInput = await screen.findByDisplayValue("Sergio Oviedo");
    await user.clear(displayNameInput);
    await user.type(displayNameInput, "Ing. Sergio Oviedo");
    await user.selectOptions(screen.getByDisplayValue("Español"), "en");
    await user.click(screen.getByRole("button", { name: "Guardar perfil" }));

    await waitFor(() => {
      expect(updateProfile).toHaveBeenCalledWith({
        email: "soviedo@ucenfotec.ac.cr",
        displayName: "Ing. Sergio Oviedo",
        settings: {
          preferredLanguage: "en",
        },
      });
    });

    expect(await screen.findByText("Tu perfil se actualizó correctamente.")).toBeInTheDocument();
  }, 10000);

  it("validates the password confirmation before calling the API", async () => {
    const user = userEvent.setup();

    render(<ProfileSettingsPanel />);

    await screen.findByDisplayValue("Sergio Oviedo");
    await user.type(screen.getByLabelText("Contraseña actual"), "1234ABC");
    await user.type(screen.getByLabelText("Nueva contraseña"), "ZXCV1234");
    await user.type(screen.getByLabelText("Confirmar nueva contraseña"), "ZXCV0000");
    await user.click(screen.getByRole("button", { name: "Actualizar contraseña" }));

    expect(changePassword).not.toHaveBeenCalled();
    expect(
      await screen.findByText("La confirmación de la nueva contraseña no coincide."),
    ).toBeInTheDocument();
  });

  it("returns to the current main panel", async () => {
    const user = userEvent.setup();

    render(<ProfileSettingsPanel />);

    await user.click(await screen.findByRole("button", { name: "Volver al panel principal" }));

    await waitFor(() => {
      expect(pushMock).toHaveBeenCalledWith("/admin");
    });
  });
});
