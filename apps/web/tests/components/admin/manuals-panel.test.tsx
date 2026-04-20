import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ManualsPanel } from "@/features/admin/manuals-panel";
import {
  deleteManual,
  fetchAdminStatus,
  fetchManuals,
  getManualOpenUrl,
  updateManual,
  uploadManual,
} from "@/lib/manuals";

vi.mock("@/lib/manuals", () => ({
  fetchAdminStatus: vi.fn(),
  fetchManuals: vi.fn(),
  uploadManual: vi.fn(),
  updateManual: vi.fn(),
  deleteManual: vi.fn(),
  getManualOpenUrl: vi.fn(),
}));

describe("ManualsPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(fetchAdminStatus).mockResolvedValue({
      manualsIndexed: 2,
      activeUsers: 5,
      pendingJobs: 1,
    });
    vi.mocked(fetchManuals).mockResolvedValue([
      {
        id: 1,
        title: "RC7 Programmer Manual I",
        originalFilename: "rc7-manual.pdf",
        storageKey: "manuals/1.pdf",
        contentType: "application/pdf",
        sizeBytes: 2400,
        status: "indexed",
        chunkCount: 12,
        robotModel: "VP-6242",
        controllerVersion: "RC7.2",
        documentLanguage: "en",
        notes: "Manual principal",
        lastError: null,
        uploadedByUserId: 1,
        uploadedByEmail: "admin@ucenfotec.ac.cr",
        indexedAt: "2026-04-20T15:00:00Z",
        createdAt: "2026-04-20T14:00:00Z",
        updatedAt: "2026-04-20T15:00:00Z",
      },
    ]);
    vi.mocked(getManualOpenUrl).mockReturnValue("http://localhost:8000/api/v1/manuals/1/file");
    vi.spyOn(window, "open").mockImplementation(() => null);
  });

  it("loads and displays the manuals list", async () => {
    render(<ManualsPanel />);

    expect(await screen.findByText("RC7 Programmer Manual I")).toBeInTheDocument();
    expect(screen.getByText("Manuales")).toBeInTheDocument();
  });

  it("opens upload modal, adds multiple files and submits", async () => {
    const user = userEvent.setup();

    vi.mocked(uploadManual).mockResolvedValue({
      id: 2,
      title: "RC7 VP-6242 Programming Guide",
      originalFilename: "RC7_VP-6242_Programming_Guide.pdf",
      storageKey: "manuals/2.pdf",
      contentType: "application/pdf",
      sizeBytes: 1200,
      status: "pending",
      chunkCount: 0,
      robotModel: "VP-6242",
      controllerVersion: "RC7",
      documentLanguage: "en",
      notes: null,
      lastError: null,
      uploadedByUserId: 1,
      uploadedByEmail: "admin@ucenfotec.ac.cr",
      indexedAt: null,
      createdAt: "2026-04-20T16:00:00Z",
      updatedAt: "2026-04-20T16:00:00Z",
    });

    render(<ManualsPanel />);

    await screen.findByText("RC7 Programmer Manual I");

    await user.click(screen.getByRole("button", { name: /subir manual/i }));
    expect(screen.getByText(/arrastra uno o varios pdf/i)).toBeInTheDocument();

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const testFile = new File(["pdf-content"], "RC7_VP-6242_Programming_Guide.pdf", {
      type: "application/pdf",
    });
    const secondFile = new File(["pdf-content-2"], "help-e.pdf", {
      type: "application/pdf",
    });
    await user.upload(fileInput, [testFile, secondFile]);

    await waitFor(() => {
      expect(screen.getByText("RC7 VP 6242 Programming Guide")).toBeInTheDocument();
      expect(screen.getByText("help e")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /subir manuales/i }));

    await waitFor(() => {
      expect(uploadManual).toHaveBeenCalledTimes(2);
      expect(uploadManual).toHaveBeenNthCalledWith(1, {
        title: "RC7 VP 6242 Programming Guide",
        file: expect.any(File),
      });
      expect(uploadManual).toHaveBeenNthCalledWith(2, {
        title: "help e",
        file: expect.any(File),
      });
    });
  });

  it("opens edit modal and updates name and notes", async () => {
    const user = userEvent.setup();
    vi.mocked(updateManual).mockResolvedValue({
      id: 1,
      title: "Manual Editado",
      originalFilename: "rc7-manual.pdf",
      storageKey: "manuals/1.pdf",
      contentType: "application/pdf",
      sizeBytes: 2400,
      status: "indexed",
      chunkCount: 12,
      robotModel: "VP-6242",
      controllerVersion: "RC7.2",
      documentLanguage: "en",
      notes: "Notas nuevas",
      lastError: null,
      uploadedByUserId: 1,
      uploadedByEmail: "admin@ucenfotec.ac.cr",
      indexedAt: "2026-04-20T15:00:00Z",
      createdAt: "2026-04-20T14:00:00Z",
      updatedAt: "2026-04-20T15:00:00Z",
    });

    render(<ManualsPanel />);
    await screen.findByText("RC7 Programmer Manual I");

    await user.click(screen.getByRole("button", { name: /editar rc7 programmer manual i/i }));
    await user.clear(screen.getByLabelText(/nombre del manual/i));
    await user.type(screen.getByLabelText(/nombre del manual/i), "Manual Editado");
    await user.clear(screen.getByLabelText(/notas/i));
    await user.type(screen.getByLabelText(/notas/i), "Notas nuevas");
    await user.click(screen.getByRole("button", { name: /^guardar$/i }));

    await waitFor(() => {
      expect(updateManual).toHaveBeenCalledWith(1, {
        title: "Manual Editado",
        notes: "Notas nuevas",
      });
    });
  });

  it("deletes a manual from confirmation modal", async () => {
    const user = userEvent.setup();
    vi.mocked(deleteManual).mockResolvedValue();

    render(<ManualsPanel />);
    await screen.findByText("RC7 Programmer Manual I");

    await user.click(screen.getByRole("button", { name: /eliminar rc7 programmer manual i/i }));
    expect(screen.getByText(/esta acción no se puede deshacer/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /^eliminar$/i }));

    await waitFor(() => {
      expect(deleteManual).toHaveBeenCalledWith(1);
    });
  });

  it("opens manual in new tab", async () => {
    const user = userEvent.setup();

    render(<ManualsPanel />);
    await screen.findByText("RC7 Programmer Manual I");

    await user.click(screen.getByRole("button", { name: /abrir rc7 programmer manual i/i }));
    expect(getManualOpenUrl).toHaveBeenCalledWith(1);
    expect(window.open).toHaveBeenCalled();
  });
});
