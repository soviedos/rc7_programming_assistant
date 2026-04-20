"use client";

import { ChangeEvent, FormEvent, useEffect, useState } from "react";
import {
  Upload,
  X,
  FileText,
  Loader2,
  Database,
  Clock,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  fetchAdminStatus,
  fetchManuals,
  uploadManual,
  type AdminStatus,
  type DocumentLanguage,
  type ManualDocument,
} from "@/lib/manuals";

// ── Types ──────────────────────────────────────────────────────────

type FlashMessage = { kind: "success" | "error"; text: string } | null;

type ManualFormState = {
  title: string;
  robotModel: string;
  controllerVersion: string;
  documentLanguage: DocumentLanguage;
  notes: string;
  file: File | null;
};

const EMPTY_FORM: ManualFormState = {
  title: "",
  robotModel: "",
  controllerVersion: "",
  documentLanguage: "es",
  notes: "",
  file: null,
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

function extractMetadataFromFile(file: File): Omit<ManualFormState, "file"> {
  const stem = file.name.replace(/\.pdf$/i, "");

  // Normalize underscores to spaces for pattern matching (keep dashes in model names)
  const normalized = stem.replace(/_+/g, " ");

  // Detect robot model (DENSO patterns: VP-6242, VS-060, etc.)
  const robotMatch = normalized.match(/\b(VP-?\d{3,5}[A-Z]?|VS-?\d{2,4}[A-Z]?)\b/i);
  const robotModel = robotMatch ? robotMatch[1].replace(/^(VP|VS)(\d)/i, "$1-$2").toUpperCase() : "";

  // Detect controller version (RC7, RC7.2, RC8, etc.)
  const ctrlMatch = normalized.match(/\b(RC-?\d+\.?\d*)\b/i);
  const controllerVersion = ctrlMatch ? ctrlMatch[1].replace(/^RC(\d)/i, "RC$1").toUpperCase() : "";

  // Detect language from filename keywords
  const hasEnglish = /\b(guide|instruction|programming|operation|reference|user)\b/i.test(normalized);
  const hasSpanish = /\b(guía|guia|instrucciones|programación|programacion|operación|operacion|usuario)\b/i.test(normalized);
  const documentLanguage: DocumentLanguage = hasSpanish && !hasEnglish ? "es" : hasEnglish ? "en" : "es";

  // Build a clean title from the filename
  const title = stem
    .replace(/[-_]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();

  return { title, robotModel, controllerVersion, documentLanguage, notes: "" };
}

// ── Upload Modal ────────────────────────────────────────────────────

function UploadModal({
  isOpen,
  onClose,
  onSuccess,
}: {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [form, setForm] = useState<ManualFormState>(EMPTY_FORM);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState<FlashMessage>(null);
  const [fileKey, setFileKey] = useState(0);
  const [isDragging, setIsDragging] = useState(false);

  function updateField<K extends keyof ManualFormState>(key: K, value: ManualFormState[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function acceptFile(file: File) {
    if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
      setMessage({ kind: "error", text: "Solo se permiten archivos PDF." });
      return;
    }
    setMessage(null);
    const meta = extractMetadataFromFile(file);
    setForm({ ...meta, file });
  }

  function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) acceptFile(file);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) acceptFile(file);
  }

  function handleRemoveFile() {
    setForm(EMPTY_FORM);
    setFileKey((k) => k + 1);
    setMessage(null);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setMessage(null);

    if (!form.file) {
      setMessage({ kind: "error", text: "Selecciona un archivo PDF." });
      return;
    }
    if (form.title.trim().length < 3) {
      setMessage({ kind: "error", text: "El título debe tener al menos 3 caracteres." });
      return;
    }

    setIsSubmitting(true);
    try {
      await uploadManual({
        title: form.title,
        file: form.file,
        robotModel: form.robotModel,
        controllerVersion: form.controllerVersion,
        documentLanguage: form.documentLanguage,
        notes: form.notes,
      });
      setForm(EMPTY_FORM);
      setFileKey((k) => k + 1);
      onSuccess();
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
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-bg-soft border border-border rounded-2xl shadow-2xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <h2 className="text-base font-semibold text-ink">Subir manual</h2>
          <button onClick={onClose} className="p-1 rounded-md text-muted hover:text-ink hover:bg-surface-hover transition-colors">
            <X className="h-4 w-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* ── Dropzone / file picker ── */}
          {!form.file ? (
            <label
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
              className={cn(
                "flex flex-col items-center justify-center gap-2 py-10 rounded-xl border-2 border-dashed cursor-pointer transition-colors",
                isDragging
                  ? "border-accent bg-accent/5"
                  : "border-border hover:border-accent/40 hover:bg-surface-hover",
              )}
            >
              <Upload className="h-8 w-8 text-muted" />
              <p className="text-sm text-muted">
                Arrastra un PDF aquí o <span className="text-accent font-medium">selecciona un archivo</span>
              </p>
              <p className="text-[11px] text-soft">Los datos se extraen automáticamente del archivo</p>
              <input
                key={fileKey}
                type="file"
                accept="application/pdf,.pdf"
                onChange={handleFileChange}
                className="sr-only"
              />
            </label>
          ) : (
            <>
              {/* ── Selected file indicator ── */}
              <div className="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-surface border border-border">
                <FileText className="h-5 w-5 text-info shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-ink font-medium truncate">{form.file.name}</p>
                  <p className="text-[11px] text-soft">{formatFileSize(form.file.size)}</p>
                </div>
                <button
                  type="button"
                  onClick={handleRemoveFile}
                  className="p-1 rounded-md text-muted hover:text-ink hover:bg-surface-hover transition-colors"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>

              {/* ── Auto-populated fields ── */}
              <p className="text-[11px] text-soft -mb-2">Datos extraídos — edita si es necesario</p>

              <div>
                <label className="block text-xs font-medium text-muted mb-1.5">Título del manual</label>
                <input
                  value={form.title}
                  onChange={(e) => updateField("title", e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-surface border border-border text-sm text-ink placeholder:text-soft focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent/40 transition-colors"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-muted mb-1.5">Modelo de robot</label>
                  <input
                    value={form.robotModel}
                    onChange={(e) => updateField("robotModel", e.target.value)}
                    placeholder="Ej. VP-6242"
                    className="w-full px-3 py-2 rounded-lg bg-surface border border-border text-sm text-ink placeholder:text-soft focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent/40 transition-colors"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-muted mb-1.5">Controlador</label>
                  <input
                    value={form.controllerVersion}
                    onChange={(e) => updateField("controllerVersion", e.target.value)}
                    placeholder="Ej. RC7"
                    className="w-full px-3 py-2 rounded-lg bg-surface border border-border text-sm text-ink placeholder:text-soft focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent/40 transition-colors"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-muted mb-1.5">Idioma</label>
                  <select
                    value={form.documentLanguage}
                    onChange={(e) => updateField("documentLanguage", e.target.value as DocumentLanguage)}
                    className="w-full px-3 py-2 rounded-lg bg-surface border border-border text-sm text-ink cursor-pointer focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent/40 transition-colors"
                  >
                    <option value="es">Español</option>
                    <option value="en">Inglés</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-muted mb-1.5">Notas (opcional)</label>
                  <input
                    value={form.notes}
                    onChange={(e) => updateField("notes", e.target.value)}
                    placeholder="Contexto adicional"
                    className="w-full px-3 py-2 rounded-lg bg-surface border border-border text-sm text-ink placeholder:text-soft focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent/40 transition-colors"
                  />
                </div>
              </div>
            </>
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
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-sm text-muted hover:text-ink hover:bg-surface-hover transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !form.file}
              className="px-4 py-2 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
            >
              {isSubmitting && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
              {isSubmitting ? "Cargando…" : "Subir manual"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Main Component ──────────────────────────────────────────────────

export function ManualsPanel() {
  const [status, setStatus] = useState<AdminStatus | null>(null);
  const [manuals, setManuals] = useState<ManualDocument[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showUpload, setShowUpload] = useState(false);

  async function loadData() {
    try {
      const [nextStatus, nextManuals] = await Promise.all([
        fetchAdminStatus(),
        fetchManuals(),
      ]);
      setStatus(nextStatus);
      setManuals(nextManuals);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible cargar los datos.");
    } finally {
      setIsLoading(false);
    }
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
                  {manual.lastError && (
                    <p className="text-[11px] text-danger mt-1.5">{manual.lastError}</p>
                  )}
                </div>
              </article>
            ))}
          </div>
        )}
      </div>

      <UploadModal
        isOpen={showUpload}
        onClose={() => setShowUpload(false)}
        onSuccess={loadData}
      />
    </div>
  );
}
