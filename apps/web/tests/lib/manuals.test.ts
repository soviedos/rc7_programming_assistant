import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  deleteManual,
  fetchAdminStatus,
  fetchManuals,
  fetchManualReviewSummaries,
  getManualOpenUrl,
  updateManual,
  uploadManual,
} from "@/lib/manuals";

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

  it("updates manual metadata", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify({
          id: 4,
          title: "Alarm Codes Updated",
          original_filename: "alarms.pdf",
          storage_key: "manuals/2026/04/20/alarms.pdf",
          content_type: "application/pdf",
          size_bytes: 1024,
          status: "pending",
          chunk_count: 0,
          robot_model: "RC7 Core",
          controller_version: "RC7.2",
          document_language: "en",
          notes: "Nueva nota",
          last_error: null,
          uploaded_by_user_id: 1,
          uploaded_by_email: "admin@ucenfotec.ac.cr",
          indexed_at: null,
          created_at: "2026-04-20T14:00:00Z",
          updated_at: "2026-04-20T14:00:00Z",
        }),
        {
          status: 200,
          headers: {
            "Content-Type": "application/json",
          },
        },
      ),
    );

    const updated = await updateManual(4, { title: "Alarm Codes Updated", notes: "Nueva nota" });

    expect(updated.title).toBe("Alarm Codes Updated");
    expect(fetch).toHaveBeenCalledTimes(1);
    const [, options] = vi.mocked(fetch).mock.calls[0];
    expect(options?.method).toBe("PUT");
  });

  it("deletes manual", async () => {
    vi.mocked(fetch).mockResolvedValue(new Response(null, { status: 204 }));

    await expect(deleteManual(8)).resolves.toBeUndefined();
    expect(fetch).toHaveBeenCalledTimes(1);
    const [, options] = vi.mocked(fetch).mock.calls[0];
    expect(options?.method).toBe("DELETE");
  });

  it("builds open URL for a manual", () => {
    expect(getManualOpenUrl(5)).toBe("http://localhost:8000/api/v1/manuals/5/file");
  });

  it("loads and normalizes manual review summaries", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify({
          items: [
            {
              manual_id: 3,
              initial_chunk_count: 20,
              final_chunk_count: 18,
              reviewed_count: 8,
              skipped_count: 2,
              error_count: 0,
              merge_actions: 1,
              split_actions: 2,
              keep_actions: 5,
              regenerate_actions: 0,
              applied_autofixes: 2,
              avg_coherence_score: 0.81,
              avg_completeness_score: 0.78,
              avg_boundary_quality_score: 0.74,
              estimated_input_tokens: 1200,
              estimated_output_tokens: 320,
              estimated_cost_usd: 0.0042,
              updated_at: "2026-04-20T14:00:00Z",
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

    await expect(fetchManualReviewSummaries()).resolves.toEqual({
      3: {
        manualId: 3,
        initialChunkCount: 20,
        finalChunkCount: 18,
        reviewedCount: 8,
        skippedCount: 2,
        errorCount: 0,
        mergeActions: 1,
        splitActions: 2,
        keepActions: 5,
        regenerateActions: 0,
        appliedAutofixes: 2,
        avgCoherenceScore: 0.81,
        avgCompletenessScore: 0.78,
        avgBoundaryQualityScore: 0.74,
        estimatedInputTokens: 1200,
        estimatedOutputTokens: 320,
        estimatedCostUsd: 0.0042,
        updatedAt: "2026-04-20T14:00:00Z",
      },
    });
  });
});
