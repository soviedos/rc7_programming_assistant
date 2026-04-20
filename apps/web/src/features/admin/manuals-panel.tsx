"use client";

import { ChangeEvent, FormEvent, useEffect, useState, type DragEvent } from "react";
import {
  Upload,
  X,
  FileText,
  Loader2,
  Database,
  Clock,
  CheckCircle2,
  AlertCircle,
  Pencil,
  Trash2,
  ExternalLink,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  fetchAdminStatus,
  fetchManuals,
  fetchManualReviewSummaries,
  getManualOpenUrl,
  deleteManual,
  updateManual,
  uploadManual,
  type AdminStatus,
  type ManualDocument,
  type ManualReviewSummary,
} from "@/lib/manuals";

// ── Types ──────────────────────────────────────────────────────────

type FlashMessage = { kind: "success" | "error"; text: string } | null;

type ManualFormState = {
  id: string;
  title: string;
  file: File;
};

type EditFormState = {
  title: string;
  notes: string;
};

const STATUS_CONFIG: Record<
  ManualDocument["status"],
  { label: string; icon: typeof CheckCircle2; className: string }
> = {
  indexed: { label: "Indexado", icon: CheckCircle2, className: "text-success bg-success/10" },
  processing: { label: "Procesando", icon: Loader2, className: "text-info bg-info/10" },
  pending: { label: "Pendiente", icon: Clock, className: "text-warning bg-warning/10" },
  failed: { label: "Error", icon: AlertCircle, className: "text-danger bg-danger/10" },
};

// ── Helpers ─────────────────────────────────────────────────────────

function formatDate(value: string | null): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat("es-CR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatUsd(value: number): string {
  return new Intl.NumberFormat("es-CR", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 4,
  }).format(value);
}

// ── Status Badge ────────────────────────────────────────────────────

function StatusBadge({ status }: { status: ManualDocument["status"] }) {
  const cfg = STATUS_CONFIG[status];
  const Icon = cfg.icon;
  return (
    <span className={cn("inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full", cfg.className)}>
      <Icon className={cn("h-3 w-3", status === "processing" && "animate-spin")} />
      {cfg.label}
    </span>
  );
}

// ── PDF metadata extraction ─────────────────────────────────────────

function extractTitleFromFile(file: File): string {
  const stem = file.name.replace(/\.pdf$/i, "");

  return stem
    .replace(/[-_]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function buildQueueItem(file: File): ManualFormState {
  return {
    id: `${file.name}-${file.size}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    file,
    title: extractTitleFromFile(file),
  };
}

// ── Upload Modal ────────────────────────────────────────────────────

function UploadModal({
  isOpen,
  onClose,
  onSuccess,
}: {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (message: string) => void;
}) {
  const [items, setItems] = useState<ManualFormState[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState<FlashMessage>(null);
  const [fileKey, setFileKey] = useState(1);
  const [isDragging, setIsDragging] = useState(false);

  function resetModal() {
    setItems([]);
    setMessage(null);
    setFileKey((k) => k + 1);
  }

  function handleAddFiles(fileList: FileList | File[]) {
    const incoming = Array.from(fileList);
    const pdfs = incoming.filter(
      (file) => file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf"),
    );

    if (pdfs.length === 0) {
      setMessage({ kind: "error", text: "Solo se permiten archivos PDF." });
      return;
    }

    if (pdfs.length < incoming.length) {
      setMessage({ kind: "error", text: "Algunos archivos fueron omitidos por no ser PDF." });
    } else {
      setMessage(null);
    }

    setItems((prev) => [...prev, ...pdfs.map(buildQueueItem)]);
  }

  function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    if (e.target.files?.length) {
      handleAddFiles(e.target.files);
      e.target.value = "";
    }
  }

  function handleDrop(e: DragEvent) {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files.length) {
      handleAddFiles(e.dataTransfer.files);
    }
  }

  function handleRemoveItem(id: string) {
    setItems((prev) => prev.filter((item) => item.id !== id));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setMessage(null);

    if (!items.length) {
      setMessage({ kind: "error", text: "Selecciona al menos un archivo PDF." });
      return;
    }

    if (items.some((item) => item.title.trim().length < 3)) {
      setMessage({ kind: "error", text: "Cada título debe tener al menos 3 caracteres." });
      return;
    }

    setIsSubmitting(true);
    try {
      for (const item of items) {
        await uploadManual({
          title: item.title,
          file: item.file,
        });
      }

      const uploadedCount = items.length;
      resetModal();
      onSuccess(
        uploadedCount === 1
          ? "Manual cargado correctamente."
          : `Se cargaron ${uploadedCount} manuales correctamente.`,
      );
      onClose();
    } catch (err) {
      setMessage({
        kind: "error",
        text: err instanceof Error ? err.message : "No fue posible cargar el manual.",
      });
    } finally {
      setIsSubmitting(false);
    }
  }

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={() => {
          resetModal();
          onClose();
        }}
      />
      <div className="relative bg-bg-soft border border-border rounded-2xl shadow-2xl w-full max-w-3xl mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <h2 className="text-base font-semibold text-ink">Subir manuales</h2>
          <button
            onClick={() => {
              resetModal();
              onClose();
            }}
            className="p-1 rounded-md text-muted hover:text-ink hover:bg-surface-hover transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <label
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            className={cn(
              "flex flex-col items-center justify-center gap-2 py-8 rounded-xl border-2 border-dashed cursor-pointer transition-colors",
              isDragging
                ? "border-accent bg-accent/5"
                : "border-border hover:border-accent/40 hover:bg-surface-hover",
            )}
          >
            <Upload className="h-8 w-8 text-muted" />
            <p className="text-sm text-muted text-center">
              Arrastra uno o varios PDF aquí o {" "}
              <span className="text-accent font-medium">selecciona archivos</span>
            </p>
            <p className="text-[11px] text-soft">Se cargan con el nombre del archivo y luego puedes editar en la lista</p>
            <input
              key={fileKey}
              type="file"
              accept="application/pdf,.pdf"
              multiple
              onChange={handleFileChange}
              className="sr-only"
            />
          </label>

          {items.length > 0 && (
            <div className="space-y-3">
              <p className="text-[11px] text-soft">Archivos listos para subir</p>
              {items.map((item) => (
                <div key={item.id} className="p-3 rounded-lg bg-surface border border-border">
                  <div className="flex items-center gap-3">
                    <FileText className="h-5 w-5 text-info shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-ink font-medium truncate">{item.title || item.file.name}</p>
                      <p className="text-[11px] text-soft truncate">{item.file.name}</p>
                      <p className="text-[11px] text-soft">{formatFileSize(item.file.size)}</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleRemoveItem(item.id)}
                      className="p-1 rounded-md text-muted hover:text-ink hover:bg-surface-hover transition-colors"
                      aria-label={`Eliminar ${item.file.name}`}
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {message && (
            <p className={cn(
              "text-xs px-3 py-2 rounded-lg",
              message.kind === "error" ? "bg-danger/10 text-danger" : "bg-success/10 text-success",
            )}>
              {message.text}
            </p>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => {
                resetModal();
                onClose();
              }}
              className="px-4 py-2 rounded-lg text-sm text-muted hover:text-ink hover:bg-surface-hover transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !items.length}
              className="px-4 py-2 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
            >
              {isSubmitting && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
              {isSubmitting ? "Cargando…" : "Subir manuales"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function EditManualModal({
  manual,
  isOpen,
  onClose,
  onSuccess,
}: {
  manual: ManualDocument | null;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (message: string) => void;
}) {
  const [form, setForm] = useState<EditFormState>({ title: "", notes: "" });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState<FlashMessage>(null);

  useEffect(() => {
    if (manual) {
      setForm({ title: manual.title, notes: manual.notes ?? "" });
      setMessage(null);
      setIsSubmitting(false);
    }
  }, [manual]);

  if (!isOpen || !manual) return null;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setMessage(null);
    const currentManual = manual;
    if (!currentManual) return;

    if (form.title.trim().length < 3) {
      setMessage({ kind: "error", text: "El nombre debe tener al menos 3 caracteres." });
      return;
    }

    setIsSubmitting(true);
    try {
      await updateManual(currentManual.id, {
        title: form.title,
        notes: form.notes,
      });
      onSuccess("Manual actualizado correctamente.");
      onClose();
    } catch (err) {
      setMessage({
        kind: "error",
        text: err instanceof Error ? err.message : "No fue posible actualizar el manual.",
      });
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-bg-soft border border-border rounded-2xl shadow-2xl w-full max-w-lg mx-4">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <h2 className="text-base font-semibold text-ink">Editar manual</h2>
          <button onClick={onClose} className="p-1 rounded-md text-muted hover:text-ink hover:bg-surface-hover transition-colors">
            <X className="h-4 w-4" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label htmlFor="edit-manual-title" className="block text-xs font-medium text-muted mb-1.5">
              Nombre del manual
            </label>
            <input
              id="edit-manual-title"
              value={form.title}
              onChange={(e) => setForm((prev) => ({ ...prev, title: e.target.value }))}
              className="w-full px-3 py-2 rounded-lg bg-surface border border-border text-sm text-ink placeholder:text-soft focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent/40 transition-colors"
            />
          </div>
          <div>
            <label htmlFor="edit-manual-notes" className="block text-xs font-medium text-muted mb-1.5">
              Notas
            </label>
            <textarea
              id="edit-manual-notes"
              value={form.notes}
              onChange={(e) => setForm((prev) => ({ ...prev, notes: e.target.value }))}
              rows={4}
              placeholder="Agrega notas adicionales"
              className="w-full px-3 py-2 rounded-lg bg-surface border border-border text-sm text-ink placeholder:text-soft focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent/40 transition-colors"
            />
          </div>

          {message && (
            <p
              className={cn(
                "text-xs px-3 py-2 rounded-lg",
                message.kind === "error" ? "bg-danger/10 text-danger" : "bg-success/10 text-success",
              )}
            >
              {message.text}
            </p>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-sm text-muted hover:text-ink hover:bg-surface-hover transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isSubmitting ? "Guardando…" : "Guardar"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function DeleteManualModal({
  manual,
  isOpen,
  onClose,
  onSuccess,
}: {
  manual: ManualDocument | null;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (message: string) => void;
}) {
  const [isDeleting, setIsDeleting] = useState(false);
  const [message, setMessage] = useState<FlashMessage>(null);

  if (!isOpen || !manual) return null;

  async function handleDelete() {
    setMessage(null);
    const currentManual = manual;
    if (!currentManual) return;
    setIsDeleting(true);
    try {
      await deleteManual(currentManual.id);
      onSuccess("Manual eliminado correctamente.");
      onClose();
    } catch (err) {
      setMessage({
        kind: "error",
        text: err instanceof Error ? err.message : "No fue posible eliminar el manual.",
      });
    } finally {
      setIsDeleting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-bg-soft border border-border rounded-2xl shadow-2xl w-full max-w-md mx-4">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <h2 className="text-base font-semibold text-ink">Eliminar manual</h2>
          <button onClick={onClose} className="p-1 rounded-md text-muted hover:text-ink hover:bg-surface-hover transition-colors">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="p-6 space-y-4">
          <p className="text-sm text-muted">
            Vas a eliminar <span className="text-ink font-medium">{manual.title}</span>. Esta acción no se puede deshacer.
          </p>

          {message && (
            <p className="text-xs px-3 py-2 rounded-lg bg-danger/10 text-danger">{message.text}</p>
          )}

          <div className="flex justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-sm text-muted hover:text-ink hover:bg-surface-hover transition-colors"
            >
              Cancelar
            </button>
            <button
              type="button"
              onClick={handleDelete}
              disabled={isDeleting}
              className="px-4 py-2 rounded-lg bg-danger text-white text-sm font-medium hover:bg-danger/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isDeleting ? "Eliminando…" : "Eliminar"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Main Component ──────────────────────────────────────────────────

export function ManualsPanel() {
  const [status, setStatus] = useState<AdminStatus | null>(null);
  const [manuals, setManuals] = useState<ManualDocument[]>([]);
  const [reviewSummaries, setReviewSummaries] = useState<Record<number, ManualReviewSummary>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<FlashMessage>(null);
  const [showUpload, setShowUpload] = useState(false);
  const [showEdit, setShowEdit] = useState(false);
  const [showDelete, setShowDelete] = useState(false);
  const [selectedManual, setSelectedManual] = useState<ManualDocument | null>(null);

  async function loadData() {
    try {
      const [nextStatus, nextManuals] = await Promise.all([
        fetchAdminStatus(),
        fetchManuals(),
      ]);
      const nextReviewSummaries = await fetchManualReviewSummaries();
      setStatus(nextStatus);
      setManuals(nextManuals);
      setReviewSummaries(nextReviewSummaries);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible cargar los datos.");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleSuccess(nextMessage: string) {
    setMessage({ kind: "success", text: nextMessage });
    await loadData();
  }

  useEffect(() => {
    loadData();
  }, []);

  const indexedCount = manuals.filter((m) => m.status === "indexed").length;
  const pendingCount = manuals.filter((m) => m.status === "pending" || m.status === "processing").length;

  return (
    <div className="flex-1 overflow-y-auto">
      {/* Header with stats */}
      <div className="px-6 py-5 border-b border-border">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold text-ink">Manuales</h2>
            <p className="text-sm text-muted mt-0.5">
              Base documental del asistente
            </p>
          </div>
          <button
            onClick={() => setShowUpload(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent-hover transition-colors"
          >
            <Upload className="h-4 w-4" />
            Subir manual
          </button>
        </div>

        {/* Inline stats */}
        <div className="flex items-center gap-6 text-sm">
          <div className="flex items-center gap-2">
            <Database className="h-4 w-4 text-muted" />
            <span className="text-muted">Total:</span>
            <span className="font-semibold text-ink">{manuals.length}</span>
          </div>
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-success" />
            <span className="text-muted">Indexados:</span>
            <span className="font-semibold text-ink">{status?.manualsIndexed ?? indexedCount}</span>
          </div>
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-warning" />
            <span className="text-muted">Pendientes:</span>
            <span className="font-semibold text-ink">{status?.pendingJobs ?? pendingCount}</span>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="p-6">
        {message && (
          <p className="mb-4 text-xs px-3 py-2 rounded-lg bg-success/10 text-success">{message.text}</p>
        )}

        {isLoading ? (
          <div className="flex items-center justify-center py-16 text-muted">
            <Loader2 className="h-5 w-5 animate-spin mr-2" />
            <span className="text-sm">Cargando manuales…</span>
          </div>
        ) : error ? (
          <div className="flex items-center justify-center py-16">
            <p className="text-sm text-danger bg-danger/10 px-4 py-2 rounded-lg">{error}</p>
          </div>
        ) : manuals.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-muted">
            <FileText className="h-10 w-10 mb-3 opacity-40" />
            <p className="text-sm">No hay manuales cargados</p>
            <p className="text-xs mt-1">Sube tu primer manual PDF para comenzar</p>
          </div>
        ) : (
          <div className="space-y-2">
            {manuals.map((manual) => (
              (() => {
                const summary = reviewSummaries[manual.id];
                return (
              <article
                key={manual.id}
                className="flex items-start gap-4 p-4 rounded-xl bg-surface border border-border hover:bg-surface-hover transition-colors"
              >
                <div className="shrink-0 w-9 h-9 rounded-lg bg-info/10 flex items-center justify-center">
                  <FileText className="h-4.5 w-4.5 text-info" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="text-sm font-medium text-ink truncate">{manual.title}</h3>
                    <StatusBadge status={manual.status} />
                  </div>
                  <p className="text-xs text-muted truncate">{manual.originalFilename}</p>
                  <div className="flex items-center gap-4 mt-1.5 text-[11px] text-soft">
                    {manual.robotModel && <span>{manual.robotModel}</span>}
                    {manual.controllerVersion && <span>{manual.controllerVersion}</span>}
                    <span>{formatFileSize(manual.sizeBytes)}</span>
                    {manual.chunkCount > 0 && <span>{manual.chunkCount} chunks</span>}
                    <span>{formatDate(manual.createdAt)}</span>
                  </div>
                  {summary && (
                    <div className="mt-2 flex flex-wrap items-center gap-3 text-[11px] text-soft">
                      <span className="px-2 py-0.5 rounded-full bg-info/10 text-info">
                        QA revisado: {summary.reviewedCount}
                      </span>
                      <span className="px-2 py-0.5 rounded-full bg-success/10 text-success">
                        Autofixes: {summary.appliedAutofixes}
                      </span>
                      <span className="px-2 py-0.5 rounded-full bg-warning/10 text-warning">
                        Costo: {formatUsd(summary.estimatedCostUsd)}
                      </span>
                    </div>
                  )}
                  {manual.notes && (
                    <p className="text-xs text-muted mt-1.5 line-clamp-2">{manual.notes}</p>
                  )}
                  {manual.lastError && (
                    <p className="text-[11px] text-danger mt-1.5">{manual.lastError}</p>
                  )}
                </div>
                <div className="shrink-0 flex items-center gap-1">
                  <button
                    type="button"
                    onClick={() => window.open(getManualOpenUrl(manual.id), "_blank", "noopener,noreferrer")}
                    className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-md text-xs text-muted hover:text-ink hover:bg-surface-hover transition-colors"
                    aria-label={`Abrir ${manual.title}`}
                  >
                    <ExternalLink className="h-3.5 w-3.5" />
                    Abrir
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedManual(manual);
                      setShowEdit(true);
                    }}
                    className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-md text-xs text-muted hover:text-ink hover:bg-surface-hover transition-colors"
                    aria-label={`Editar ${manual.title}`}
                  >
                    <Pencil className="h-3.5 w-3.5" />
                    Editar
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedManual(manual);
                      setShowDelete(true);
                    }}
                    className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-md text-xs text-danger hover:bg-danger/10 transition-colors"
                    aria-label={`Eliminar ${manual.title}`}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                    Eliminar
                  </button>
                </div>
              </article>
                );
              })()
            ))}
          </div>
        )}
      </div>

      <UploadModal
        isOpen={showUpload}
        onClose={() => setShowUpload(false)}
        onSuccess={handleSuccess}
      />
      <EditManualModal
        isOpen={showEdit}
        manual={selectedManual}
        onClose={() => {
          setShowEdit(false);
          setSelectedManual(null);
        }}
        onSuccess={handleSuccess}
      />
      <DeleteManualModal
        isOpen={showDelete}
        manual={selectedManual}
        onClose={() => {
          setShowDelete(false);
          setSelectedManual(null);
        }}
        onSuccess={handleSuccess}
      />
    </div>
  );
}
