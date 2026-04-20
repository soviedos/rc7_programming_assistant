import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ManualsPanel } from "@/features/admin/manuals-panel";
import { fetchAdminStatus, fetchManuals, uploadManual } from "@/lib/manuals";

vi.mock("@/lib/manuals", () => ({
  fetchAdminStatus: vi.fn(),
  fetchManuals: vi.fn(),
  uploadManual: vi.fn(),
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
  });

  it("loads and displays the manuals list", async () => {
    render(<ManualsPanel />);

    expect(await screen.findByText("RC7 Programmer Manual I")).toBeInTheDocument();
    expect(screen.getByText("Manuales")).toBeInTheDocument();
  });

  it("opens upload modal, auto-fills from filename, and submits", async () => {
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

    // Open upload modal — shows dropzone
    await user.click(screen.getByRole("button", { name: /subir/i }));
    expect(screen.getByText(/arrastra un pdf/i)).toBeInTheDocument();

    // Upload file — triggers auto-extraction from filename
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const testFile = new File(["pdf-content"], "RC7_VP-6242_Programming_Guide.pdf", {
      type: "application/pdf",
    });
    await user.upload(fileInput, testFile);

    // Fields should be auto-populated
    await waitFor(() => {
      expect(screen.getByDisplayValue("RC7 VP 6242 Programming Guide")).toBeInTheDocument();
      expect(screen.getByDisplayValue("VP-6242")).toBeInTheDocument();
      expect(screen.getByDisplayValue("RC7")).toBeInTheDocument();
    });

    // Submit — modal submit button is the second one
    const submitButtons = screen.getAllByRole("button", { name: /subir manual/i });
    await user.click(submitButtons[submitButtons.length - 1]);

    await waitFor(() => {
      expect(uploadManual).toHaveBeenCalledWith({
        title: "RC7 VP 6242 Programming Guide",
        file: expect.any(File),
        robotModel: "VP-6242",
        controllerVersion: "RC7",
        documentLanguage: "en",
        notes: "",
      });
    });
  });
});
