import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ManualsPanel } from "@/features/admin/manuals-panel";
import {
  cleanupStaleProcessing,
  deleteManual,
  fetchAdminStatus,
  fetchManuals,
  fetchManualReviewSummaries,
  getManualOpenUrl,
  retryManual,
  updateManual,
  uploadManual,
} from "@/lib/manuals";

vi.mock("@/lib/manuals", () => ({
  cleanupStaleProcessing: vi.fn(),
  fetchAdminStatus: vi.fn(),
  fetchManuals: vi.fn(),
  fetchManualReviewSummaries: vi.fn(),
  uploadManual: vi.fn(),
  updateManual: vi.fn(),
  deleteManual: vi.fn(),
  retryManual: vi.fn(),
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
        sha256: "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        status: "indexed",
        chunkCount: 12,
        robotModel: "VP-6242",
        controllerVersion: "RC7.2",
        documentLanguage: "en",
        categories: [],
        notes: "Manual principal",
        lastError: null,
        uploadedByUserId: 1,
        uploadedByEmail: "admin@ucenfotec.ac.cr",
        processingStartedAt: "2026-04-20 14:00:00.000000",
        indexedAt: "2026-04-20T15:00:00Z",
        createdAt: "2026-04-20T14:00:00Z",
        updatedAt: "2026-04-20T15:00:00Z",
      },
    ]);
    vi.mocked(fetchManualReviewSummaries).mockResolvedValue({
      1: {
        manualId: 1,
        initialChunkCount: 13,
        finalChunkCount: 12,
        reviewedCount: 7,
        skippedCount: 1,
        errorCount: 0,
        mergeActions: 1,
        splitActions: 1,
        keepActions: 5,
        regenerateActions: 0,
        appliedAutofixes: 2,
        avgCoherenceScore: 0.83,
        avgCompletenessScore: 0.8,
        avgBoundaryQualityScore: 0.75,
        estimatedInputTokens: 1200,
        estimatedOutputTokens: 240,
        estimatedCostUsd: 0.0123,
        updatedAt: "2026-04-20T15:00:00Z",
      },
    });
    vi.mocked(getManualOpenUrl).mockReturnValue("http://localhost:8000/api/v1/manuals/1/file");
    vi.spyOn(window, "open").mockImplementation(() => null);
  });

  it("loads and displays the manuals list", async () => {
    render(<ManualsPanel />);

    expect(await screen.findByText("RC7 Programmer Manual I")).toBeInTheDocument();
    expect(screen.getByText("Manuales")).toBeInTheDocument();
    expect(screen.getByText(/QA revisado: 7/i)).toBeInTheDocument();
    expect(
      screen.getByText(
        /SHA-256: 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef/i,
      ),
    ).toBeInTheDocument();
    expect(screen.getByText(/Duración final de indexación: 60m 0s/i)).toBeInTheDocument();
  });

  it("copies SHA-256 and shows copied feedback", async () => {
    const user = userEvent.setup();
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText },
      configurable: true,
    });

    render(<ManualsPanel />);
    await screen.findByText("RC7 Programmer Manual I");

    await user.click(screen.getByRole("button", { name: /copiar sha-256 de rc7 programmer manual i/i }));

    await waitFor(() => {
      expect(writeText).toHaveBeenCalledWith(
        "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
      );
    });
    expect(screen.getByRole("button", { name: /copiar sha-256 de rc7 programmer manual i/i })).toHaveTextContent(
      /copiado/i,
    );
  });

  it("runs admin cleanup for stale processing manuals", async () => {
    const user = userEvent.setup();
    vi.mocked(cleanupStaleProcessing).mockResolvedValue({
      recovered: 2,
      manualIds: [23, 25],
    });

    render(<ManualsPanel />);

    await screen.findByText("RC7 Programmer Manual I");
    await user.click(screen.getByRole("button", { name: /limpiar processing atascados/i }));

    await waitFor(() => {
      expect(cleanupStaleProcessing).toHaveBeenCalledWith(10);
    });

    expect(
      await screen.findByText(/Se reencolaron 2 manual\(es\) atascados en processing\./i),
    ).toBeInTheDocument();
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
      categories: [],
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
      categories: [],
      notes: "Notas nuevas",
      lastError: null,
      uploadedByUserId: 1,
      uploadedByEmail: "admin@ucenfotec.ac.cr",
      processingStartedAt: "2026-04-20T14:00:00Z",
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
        categories: [],
      });
    });
  });

  it("asks to upload as new version when duplicate SHA-256 is detected", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "confirm").mockReturnValueOnce(true);

    vi.mocked(uploadManual)
      .mockRejectedValueOnce(
        new Error(
          "Ya existe un manual con el mismo SHA-256 (manual #1). Confirma 'cargar como nueva version' para continuar o cancela la carga.",
        ),
      )
      .mockResolvedValueOnce({
        id: 2,
        title: "RC7 VP 6242 Programming Guide",
        originalFilename: "RC7_VP-6242_Programming_Guide.pdf",
        storageKey: "manuals/2.pdf",
        contentType: "application/pdf",
        sizeBytes: 1200,
        status: "pending",
        chunkCount: 0,
        robotModel: null,
        controllerVersion: null,
        documentLanguage: "en",
        categories: [],
        notes: "Nueva version de manual #1 (SHA-256 duplicado).",
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

    const fileInput = document.querySelector("input[type='file']") as HTMLInputElement;
    const testFile = new File(["pdf-content"], "RC7_VP-6242_Programming_Guide.pdf", {
      type: "application/pdf",
    });
    await user.upload(fileInput, testFile);

    await waitFor(() => {
      expect(screen.getByText("RC7 VP 6242 Programming Guide")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /subir manuales/i }));

    await waitFor(() => {
      expect(window.confirm).toHaveBeenCalled();
      expect(uploadManual).toHaveBeenNthCalledWith(1, {
        title: "RC7 VP 6242 Programming Guide",
        file: expect.any(File),
      });
      expect(uploadManual).toHaveBeenNthCalledWith(2, {
        title: "RC7 VP 6242 Programming Guide",
        file: expect.any(File),
        asNewVersion: true,
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

  it("retries a failed manual", async () => {
    const user = userEvent.setup();
    vi.mocked(fetchManuals).mockResolvedValueOnce([
      {
        id: 3,
        title: "Manual Fallido",
        originalFilename: "failed.pdf",
        storageKey: "manuals/3.pdf",
        contentType: "application/pdf",
        sizeBytes: 1400,
        status: "failed",
        chunkCount: 0,
        robotModel: null,
        controllerVersion: null,
        documentLanguage: "es",
        categories: [],
        notes: null,
        lastError: "The read operation timed out",
        uploadedByUserId: 1,
        uploadedByEmail: "admin@ucenfotec.ac.cr",
        indexedAt: null,
        createdAt: "2026-04-20T16:00:00Z",
        updatedAt: "2026-04-20T16:00:00Z",
      },
    ]);
    vi.mocked(fetchManualReviewSummaries).mockResolvedValueOnce({});
    vi.mocked(retryManual).mockResolvedValue({
      id: 3,
      title: "Manual Fallido",
      originalFilename: "failed.pdf",
      storageKey: "manuals/3.pdf",
      contentType: "application/pdf",
      sizeBytes: 1400,
      status: "pending",
      chunkCount: 0,
      robotModel: null,
      controllerVersion: null,
      documentLanguage: "es",
      categories: [],
      notes: null,
      lastError: null,
      uploadedByUserId: 1,
      uploadedByEmail: "admin@ucenfotec.ac.cr",
      indexedAt: null,
      createdAt: "2026-04-20T16:00:00Z",
      updatedAt: "2026-04-20T16:01:00Z",
    });

    render(<ManualsPanel />);

    expect(await screen.findByText("Manual Fallido")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /reintentar manual fallido/i }));

    await waitFor(() => {
      expect(retryManual).toHaveBeenCalledWith(3);
    });
  });

  it("shows progress and QA pending hint for pending manuals", async () => {
    vi.mocked(fetchManuals).mockResolvedValueOnce([
      {
        id: 2,
        title: "Manual en cola",
        originalFilename: "manual-cola.pdf",
        storageKey: "manuals/2.pdf",
        contentType: "application/pdf",
        sizeBytes: 1024,
        status: "pending",
        chunkCount: 0,
        robotModel: null,
        controllerVersion: null,
        documentLanguage: "es",
        categories: [],
        notes: null,
        lastError: null,
        uploadedByUserId: 1,
        uploadedByEmail: "admin@ucenfotec.ac.cr",
        indexedAt: null,
        createdAt: "2026-04-20T16:30:00Z",
        updatedAt: "2026-04-20T16:30:00Z",
      },
    ]);
    vi.mocked(fetchManualReviewSummaries).mockResolvedValueOnce({});

    render(<ManualsPanel />);

    expect(await screen.findByText("Manual en cola")).toBeInTheDocument();
    expect(screen.getByText(/Avance: En cola/i)).toBeInTheDocument();
    expect(screen.getByText(/QA en espera/i)).toBeInTheDocument();
  });

  it("shows elapsed processing time for processing manuals", async () => {
    const now = Date.now();

    vi.mocked(fetchManuals).mockResolvedValueOnce([
      {
        id: 4,
        title: "Manual procesando",
        originalFilename: "processing.pdf",
        storageKey: "manuals/4.pdf",
        contentType: "application/pdf",
        sizeBytes: 2048,
        status: "processing",
        chunkCount: 0,
        robotModel: null,
        controllerVersion: null,
        documentLanguage: "es",
        categories: [],
        notes: null,
        lastError: null,
        uploadedByUserId: 1,
        uploadedByEmail: "admin@ucenfotec.ac.cr",
        processingStartedAt: "2026-04-21 02:51:00.226012",
        indexedAt: null,
        createdAt: new Date(now - 120_000).toISOString(),
        updatedAt: new Date(now - 120_000).toISOString(),
      },
    ]);
    vi.mocked(fetchManualReviewSummaries).mockResolvedValueOnce({});

    render(<ManualsPanel />);

    expect(await screen.findByText("Manual procesando")).toBeInTheDocument();
    expect(screen.getByText(/procesando hace/i)).toBeInTheDocument();
    expect(screen.getByText(/Tiempo consumido de indexación:/i)).toBeInTheDocument();
  });
});
