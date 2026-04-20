import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { RolesPanel } from "@/features/admin/roles-panel";
import {
  createRolePermission,
  deleteRolePermission,
  fetchRolePermissions,
} from "@/lib/roles";

vi.mock("@/lib/roles", () => ({
  fetchRolePermissions: vi.fn(),
  createRolePermission: vi.fn(),
  updateRolePermission: vi.fn(),
  deleteRolePermission: vi.fn(),
}));

describe("RolesPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(fetchRolePermissions).mockResolvedValue([
      {
        id: 1,
        key: "manuals",
        name: "Manuales",
        description: "Ver, subir y gestionar la base documental.",
        admin: true,
        user: false,
      },
    ]);
  });

  it("loads and displays permissions", async () => {
    render(<RolesPanel />);

    expect(await screen.findByText("Manuales")).toBeInTheDocument();
    expect(screen.getByText("Roles y permisos")).toBeInTheDocument();
  });

  it("opens create modal and submits a new permission", async () => {
    const user = userEvent.setup();

    vi.mocked(createRolePermission).mockResolvedValue({
      id: 2,
      key: "reports",
      name: "Reportes",
      description: "Acceso a reportes",
      admin: true,
      user: true,
    });

    vi.mocked(fetchRolePermissions)
      .mockResolvedValueOnce([
        {
          id: 1,
          key: "manuals",
          name: "Manuales",
          description: "Ver, subir y gestionar la base documental.",
          admin: true,
          user: false,
        },
      ])
      .mockResolvedValueOnce([
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
          key: "reports",
          name: "Reportes",
          description: "Acceso a reportes",
          admin: true,
          user: true,
        },
      ]);

    render(<RolesPanel />);
    await screen.findByText("Manuales");

    await user.click(screen.getByRole("button", { name: /nuevo permiso/i }));
    expect(screen.getByText("Crear permiso")).toBeInTheDocument();

    await user.type(screen.getByPlaceholderText("Ej: reports"), "reports");
    await user.type(screen.getByPlaceholderText("Ej: Reportes"), "Reportes");
    await user.type(
      screen.getByPlaceholderText("Describe que habilita este permiso"),
      "Acceso a reportes",
    );

    await user.click(screen.getByLabelText("Usuario habilitado"));
    await user.click(screen.getByRole("button", { name: /^guardar$/i }));

    await waitFor(() => {
      expect(createRolePermission).toHaveBeenCalledWith({
        key: "reports",
        name: "Reportes",
        description: "Acceso a reportes",
        admin: true,
        user: true,
      });
    });

    await screen.findByText("Permiso creado correctamente.");
  });

  it("opens delete modal and confirms permission deletion", async () => {
    const user = userEvent.setup();

    vi.mocked(deleteRolePermission).mockResolvedValue();
    vi.mocked(fetchRolePermissions)
      .mockResolvedValueOnce([
        {
          id: 1,
          key: "manuals",
          name: "Manuales",
          description: "Ver, subir y gestionar la base documental.",
          admin: true,
          user: false,
        },
      ])
      .mockResolvedValueOnce([]);

    render(<RolesPanel />);
    await screen.findByText("Manuales");

    await user.click(screen.getByRole("button", { name: /eliminar manuales/i }));
    expect(screen.getByText("Eliminar permiso")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /^eliminar$/i }));

    await waitFor(() => {
      expect(deleteRolePermission).toHaveBeenCalledWith(1);
    });

    await screen.findByText("Permiso eliminado correctamente.");
  });
});
