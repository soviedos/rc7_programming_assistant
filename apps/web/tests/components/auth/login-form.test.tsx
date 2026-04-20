import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { LoginForm } from "@/features/auth/login-form";
import { loginWithPassword } from "@/lib/auth";

const replaceMock = vi.fn();
const refreshMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    replace: replaceMock,
    push: vi.fn(),
  }),
}));

vi.mock("@/lib/auth", () => ({
  getRolePath: (role: "admin" | "user") => (role === "admin" ? "/admin/manuals" : "/chat"),
  loginWithPassword: vi.fn(),
}));

vi.mock("@/features/auth/session-provider", () => ({
  useSession: () => ({
    session: null,
    isLoading: false,
    refresh: refreshMock,
  }),
}));

describe("LoginForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    refreshMock.mockResolvedValue(undefined);
  });

  it("shows a friendly validation message and clears invalid credentials", async () => {
    const user = userEvent.setup();

    render(<LoginForm />);

    const emailInput = screen.getByPlaceholderText("correo@ejemplo.com");
    const passwordInput = screen.getByPlaceholderText("••••••••");

    await user.type(emailInput, "correo-invalido");
    await user.type(passwordInput, "123456");
    await user.click(screen.getByRole("button", { name: "Iniciar sesión" }));

    expect(await screen.findByText("Ingresa un correo válido.")).toBeInTheDocument();
    expect(emailInput).toHaveValue("");
    expect(passwordInput).toHaveValue("");
  }, 10000);

  it("allows showing and hiding the password", async () => {
    const user = userEvent.setup();

    render(<LoginForm />);

    const passwordInput = screen.getByPlaceholderText("••••••••");
    await user.type(passwordInput, "1234ABC");

    expect(passwordInput).toHaveAttribute("type", "password");

    await user.click(screen.getByRole("button", { name: "Mostrar contraseña" }));
    expect(passwordInput).toHaveAttribute("type", "text");

    await user.click(screen.getByRole("button", { name: "Ocultar contraseña" }));
    expect(passwordInput).toHaveAttribute("type", "password");
  });

  it("clears the form and shows the API error when login fails", async () => {
    const user = userEvent.setup();
    vi.mocked(loginWithPassword).mockRejectedValue(new Error("Credenciales invalidas."));

    render(<LoginForm />);

    const emailInput = screen.getByPlaceholderText("correo@ejemplo.com");
    const passwordInput = screen.getByPlaceholderText("••••••••");

    await user.type(emailInput, "soviedo@ucenfotec.ac.cr");
    await user.type(passwordInput, "1234ABC");
    await user.click(screen.getByRole("button", { name: "Mostrar contraseña" }));
    await user.click(screen.getByRole("button", { name: "Iniciar sesión" }));

    expect(await screen.findByText("Credenciales invalidas.")).toBeInTheDocument();
    expect(emailInput).toHaveValue("");
    expect(passwordInput).toHaveValue("");
  });

  it("redirects to the page associated with the active role after login", async () => {
    const user = userEvent.setup();
    vi.mocked(loginWithPassword).mockResolvedValue({
      email: "soviedo@ucenfotec.ac.cr",
      displayName: "Sergio Oviedo",
      role: "admin",
      availableRoles: ["admin", "user"],
      redirectPath: "/admin",
    });

    render(<LoginForm />);

    await user.type(screen.getByPlaceholderText("correo@ejemplo.com"), "soviedo@ucenfotec.ac.cr");
    await user.type(screen.getByPlaceholderText("••••••••"), "1234ABC");
    await user.click(screen.getByRole("button", { name: "Iniciar sesión" }));

    await waitFor(() => {
      expect(replaceMock).toHaveBeenCalledWith("/admin/manuals");
    });
  });
});
