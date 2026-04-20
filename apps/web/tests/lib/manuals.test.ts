import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { fetchAdminStatus, fetchManuals, uploadManual } from "@/lib/manuals";

describe("manuals helpers", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("loads and normalizes the admin status", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify({
          manuals_indexed: 6,
          active_users: 4,
          pending_jobs: 2,
        }),
        {
          status: 200,
          headers: {
            "Content-Type": "application/json",
          },
        },
      ),
    );

    await expect(fetchAdminStatus()).resolves.toEqual({
      manualsIndexed: 6,
      activeUsers: 4,
      pendingJobs: 2,
    });
  });

  it("loads and normalizes the manuals list", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify({
          items: [
            {
              id: 3,
              title: "RC7 Programmer Manual I",
              original_filename: "rc7-manual.pdf",
              storage_key: "manuals/2026/04/20/abc.pdf",
              content_type: "application/pdf",
              size_bytes: 2048,
              status: "indexed",
              chunk_count: 18,
              robot_model: "VP-6242",
              controller_version: "RC7.2",
              document_language: "en",
              notes: "Manual principal",
              last_error: null,
              uploaded_by_user_id: 1,
              uploaded_by_email: "admin@ucenfotec.ac.cr",
              indexed_at: "2026-04-20T15:00:00Z",
              created_at: "2026-04-20T14:00:00Z",
              updated_at: "2026-04-20T15:00:00Z",
            },
          ],
          total: 1,
        }),
        {
          status: 200,
          headers: {
            "Content-Type": "application/json",
          },
        },
      ),
    );

    await expect(fetchManuals()).resolves.toEqual([
      {
        id: 3,
        title: "RC7 Programmer Manual I",
        originalFilename: "rc7-manual.pdf",
        storageKey: "manuals/2026/04/20/abc.pdf",
        contentType: "application/pdf",
        sizeBytes: 2048,
        status: "indexed",
        chunkCount: 18,
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

  it("uploads a manual using form data", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify({
          id: 4,
          title: "Alarm Codes",
          original_filename: "alarms.pdf",
          storage_key: "manuals/2026/04/20/alarms.pdf",
          content_type: "application/pdf",
          size_bytes: 1024,
          status: "pending",
          chunk_count: 0,
          robot_model: "RC7 Core",
          controller_version: "RC7.2",
          document_language: "en",
          notes: null,
          last_error: null,
          uploaded_by_user_id: 1,
          uploaded_by_email: "admin@ucenfotec.ac.cr",
          indexed_at: null,
          created_at: "2026-04-20T14:00:00Z",
          updated_at: "2026-04-20T14:00:00Z",
        }),
        {
          status: 201,
          headers: {
            "Content-Type": "application/json",
          },
        },
      ),
    );

    const file = new File(["pdf-content"], "alarms.pdf", { type: "application/pdf" });
    const manual = await uploadManual({
      title: "Alarm Codes",
      file,
      robotModel: "RC7 Core",
      controllerVersion: "RC7.2",
      documentLanguage: "en",
    });

    expect(manual.title).toBe("Alarm Codes");
    expect(fetch).toHaveBeenCalledTimes(1);

    const [, options] = vi.mocked(fetch).mock.calls[0];
    expect(options?.method).toBe("POST");
    expect(options?.credentials).toBe("include");
    expect(options?.body).toBeInstanceOf(FormData);
  });
});
