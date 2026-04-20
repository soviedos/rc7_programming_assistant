import { api } from "@/lib/api-client";

// ── Types ──────────────────────────────────────────────────────────

export type ManualStatus = "pending" | "processing" | "indexed" | "failed";
export type DocumentLanguage = "es" | "en";

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
  status: ManualStatus;
  chunkCount: number;
  robotModel: string | null;
  controllerVersion: string | null;
  documentLanguage: DocumentLanguage;
  notes: string | null;
  lastError: string | null;
  uploadedByUserId: number;
  uploadedByEmail: string;
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
  notes?: string;
};

export type UpdateManualInput = {
  title: string;
  notes?: string;
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
  status: ManualStatus;
  chunk_count: number;
  robot_model: string | null;
  controller_version: string | null;
  document_language: DocumentLanguage;
  notes: string | null;
  last_error: string | null;
  uploaded_by_user_id: number;
  uploaded_by_email: string;
  indexed_at: string | null;
  created_at: string;
  updated_at: string;
};

type ManualListApiResponse = {
  items: ManualApiResponse[];
  total: number;
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
    status: raw.status,
    chunkCount: raw.chunk_count,
    robotModel: raw.robot_model,
    controllerVersion: raw.controller_version,
    documentLanguage: raw.document_language,
    notes: raw.notes,
    lastError: raw.last_error,
    uploadedByUserId: raw.uploaded_by_user_id,
    uploadedByEmail: raw.uploaded_by_email,
    indexedAt: raw.indexed_at,
    createdAt: raw.created_at,
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

export function getManualOpenUrl(manualId: number): string {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
  return `${baseUrl}/api/v1/manuals/${manualId}/file`;
}
