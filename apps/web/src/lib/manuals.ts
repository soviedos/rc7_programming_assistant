import { api } from "@/lib/api-client";

// ── Types ──────────────────────────────────────────────────────────

export type ManualStatus = "pending" | "processing" | "indexed" | "failed";
export type DocumentLanguage = "es" | "en";
export type ManualCategory = "startup" | "programming" | "robot_specs" | "errors";

export type AdminStatus = {
  manualsIndexed: number;
  activeUsers: number;
  pendingJobs: number;
};

export type ManualDocument = {
  id: number;
  title: string;
  originalFilename: string;
  storageKey: string;
  contentType: string;
  sizeBytes: number;
  sha256: string | null;
  status: ManualStatus;
  chunkCount: number;
  robotModel: string | null;
  controllerVersion: string | null;
  documentLanguage: DocumentLanguage;
  categories: ManualCategory[];
  notes: string | null;
  lastError: string | null;
  uploadedByUserId: number;
  uploadedByEmail: string;
  processingStartedAt: string | null;
  indexedAt: string | null;
  createdAt: string;
  updatedAt: string;
};

export type UploadManualInput = {
  title: string;
  file: File;
  robotModel?: string;
  controllerVersion?: string;
  documentLanguage?: DocumentLanguage;
  categories?: ManualCategory[];
  notes?: string;
  asNewVersion?: boolean;
};

export type UpdateManualInput = {
  title: string;
  notes?: string;
  categories?: ManualCategory[];
};

export type ManualReviewSummary = {
  manualId: number;
  initialChunkCount: number;
  finalChunkCount: number;
  reviewedCount: number;
  skippedCount: number;
  errorCount: number;
  mergeActions: number;
  splitActions: number;
  keepActions: number;
  regenerateActions: number;
  appliedAutofixes: number;
  avgCoherenceScore: number | null;
  avgCompletenessScore: number | null;
  avgBoundaryQualityScore: number | null;
  estimatedInputTokens: number;
  estimatedOutputTokens: number;
  estimatedCostUsd: number;
  updatedAt: string;
};

export type StaleProcessingCleanupResult = {
  recovered: number;
  manualIds: number[];
};

// ── API response shapes ────────────────────────────────────────────

type AdminStatusApiResponse = {
  manuals_indexed: number;
  active_users: number;
  pending_jobs: number;
};

type ManualApiResponse = {
  id: number;
  title: string;
  original_filename: string;
  storage_key: string;
  content_type: string;
  size_bytes: number;
  sha256: string | null;
  status: ManualStatus;
  chunk_count: number;
  robot_model: string | null;
  controller_version: string | null;
  document_language: DocumentLanguage;
  categories: ManualCategory[];
  notes: string | null;
  last_error: string | null;
  uploaded_by_user_id: number;
  uploaded_by_email: string;
  processing_started_at: string | null;
  indexed_at: string | null;
  created_at: string;
  updated_at: string;
};

type ManualListApiResponse = {
  items: ManualApiResponse[];
  total: number;
};

type ManualReviewSummaryApiResponse = {
  manual_id: number;
  initial_chunk_count: number;
  final_chunk_count: number;
  reviewed_count: number;
  skipped_count: number;
  error_count: number;
  merge_actions: number;
  split_actions: number;
  keep_actions: number;
  regenerate_actions: number;
  applied_autofixes: number;
  avg_coherence_score: number | null;
  avg_completeness_score: number | null;
  avg_boundary_quality_score: number | null;
  estimated_input_tokens: number;
  estimated_output_tokens: number;
  estimated_cost_usd: number;
  updated_at: string;
};

type ManualReviewSummaryListApiResponse = {
  items: ManualReviewSummaryApiResponse[];
  total: number;
};

type StaleProcessingCleanupApiResponse = {
  recovered: number;
  manual_ids: number[];
};

// ── Normalizers ────────────────────────────────────────────────────

function normalizeAdminStatus(raw: AdminStatusApiResponse): AdminStatus {
  return {
    manualsIndexed: raw.manuals_indexed,
    activeUsers: raw.active_users,
    pendingJobs: raw.pending_jobs,
  };
}

function normalizeManual(raw: ManualApiResponse): ManualDocument {
  return {
    id: raw.id,
    title: raw.title,
    originalFilename: raw.original_filename,
    storageKey: raw.storage_key,
    contentType: raw.content_type,
    sizeBytes: raw.size_bytes,
    sha256: raw.sha256,
    status: raw.status,
    chunkCount: raw.chunk_count,
    robotModel: raw.robot_model,
    controllerVersion: raw.controller_version,
    documentLanguage: raw.document_language,
    categories: raw.categories ?? [],
    notes: raw.notes,
    lastError: raw.last_error,
    uploadedByUserId: raw.uploaded_by_user_id,
    uploadedByEmail: raw.uploaded_by_email,
    processingStartedAt: raw.processing_started_at,
    indexedAt: raw.indexed_at,
    createdAt: raw.created_at,
    updatedAt: raw.updated_at,
  };
}

function normalizeManualReviewSummary(
  raw: ManualReviewSummaryApiResponse,
): ManualReviewSummary {
  return {
    manualId: raw.manual_id,
    initialChunkCount: raw.initial_chunk_count,
    finalChunkCount: raw.final_chunk_count,
    reviewedCount: raw.reviewed_count,
    skippedCount: raw.skipped_count,
    errorCount: raw.error_count,
    mergeActions: raw.merge_actions,
    splitActions: raw.split_actions,
    keepActions: raw.keep_actions,
    regenerateActions: raw.regenerate_actions,
    appliedAutofixes: raw.applied_autofixes,
    avgCoherenceScore: raw.avg_coherence_score,
    avgCompletenessScore: raw.avg_completeness_score,
    avgBoundaryQualityScore: raw.avg_boundary_quality_score,
    estimatedInputTokens: raw.estimated_input_tokens,
    estimatedOutputTokens: raw.estimated_output_tokens,
    estimatedCostUsd: raw.estimated_cost_usd,
    updatedAt: raw.updated_at,
  };
}

// ── API calls ──────────────────────────────────────────────────────

export async function fetchAdminStatus(): Promise<AdminStatus> {
  const raw = await api.get<AdminStatusApiResponse>(
    "/api/v1/admin/status",
    "No fue posible cargar el estado administrativo.",
  );
  return normalizeAdminStatus(raw);
}

export async function fetchManuals(): Promise<ManualDocument[]> {
  const raw = await api.get<ManualListApiResponse>(
    "/api/v1/manuals",
    "No fue posible cargar la base documental.",
  );
  return raw.items.map(normalizeManual);
}

export async function fetchManualReviewSummaries(): Promise<
  Record<number, ManualReviewSummary>
> {
  const raw = await api.get<ManualReviewSummaryListApiResponse>(
    "/api/v1/manuals/review-summaries",
    "No fue posible cargar el resumen de QA de manuales.",
  );

  return raw.items.reduce<Record<number, ManualReviewSummary>>((acc, item) => {
    const normalized = normalizeManualReviewSummary(item);
    acc[normalized.manualId] = normalized;
    return acc;
  }, {});
}

export async function uploadManual(
  input: UploadManualInput,
): Promise<ManualDocument> {
  const formData = new FormData();
  formData.set("title", input.title.trim());
  formData.set("file", input.file);

  if (input.robotModel?.trim()) {
    formData.set("robot_model", input.robotModel.trim());
  }
  if (input.controllerVersion?.trim()) {
    formData.set("controller_version", input.controllerVersion.trim());
  }
  formData.set("document_language", input.documentLanguage ?? "es");
  if (input.notes?.trim()) {
    formData.set("notes", input.notes.trim());
  }
  for (const cat of (input.categories ?? [])) {
    formData.append("category", cat);
  }
  if (input.asNewVersion) {
    formData.set("as_new_version", "true");
  }

  const raw = await api.postFormData<ManualApiResponse>(
    "/api/v1/manuals",
    formData,
    "No fue posible cargar el manual.",
  );
  return normalizeManual(raw);
}

export async function updateManual(
  manualId: number,
  input: UpdateManualInput,
): Promise<ManualDocument> {
  const raw = await api.put<ManualApiResponse>(
    `/api/v1/manuals/${manualId}`,
    {
      title: input.title.trim(),
      notes: input.notes?.trim() || null,
      categories: input.categories ?? [],
    },
    "No fue posible actualizar el manual.",
  );
  return normalizeManual(raw);
}

export async function deleteManual(manualId: number): Promise<void> {
  await api.deleteVoid(
    `/api/v1/manuals/${manualId}`,
    "No fue posible eliminar el manual.",
  );
}

export async function retryManual(manualId: number): Promise<ManualDocument> {
  const raw = await api.post<ManualApiResponse>(
    `/api/v1/manuals/${manualId}/retry`,
    undefined,
    "No fue posible reintentar el manual.",
  );
  return normalizeManual(raw);
}

export async function cleanupStaleProcessing(
  olderThanMinutes: number = 10,
): Promise<StaleProcessingCleanupResult> {
  const raw = await api.post<StaleProcessingCleanupApiResponse>(
    `/api/v1/manuals/cleanup-stale-processing?older_than_minutes=${olderThanMinutes}`,
    undefined,
    "No fue posible limpiar manuales atascados.",
  );

  return {
    recovered: raw.recovered,
    manualIds: raw.manual_ids,
  };
}

export function getManualOpenUrl(manualId: number): string {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
  return `${baseUrl}/api/v1/manuals/${manualId}/file`;
}
