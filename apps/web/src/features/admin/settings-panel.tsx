"use client";

import { useEffect, useState } from "react";
import { Loader2, RotateCcw, Save } from "lucide-react";

import {
  fetchSettings,
  resetSettings,
  updateSetting,
  type SystemSetting,
} from "@/lib/admin-settings";

type FlashMessage = { kind: "success" | "error"; text: string } | null;

const NUMERIC_KEYS = new Set([
  "gemini_max_tokens",
  "gemini_timeout_seconds",
  "rag_top_k_chunks",
  "rag_context_budget_chars",
  "history_max_entries",
]);

const FLOAT_KEYS = new Set(["gemini_temperature"]);

const LABEL_MAP: Record<string, string> = {
  gemini_temperature: "Temperatura (Gemini)",
  gemini_max_tokens: "Tokens máximos",
  gemini_timeout_seconds: "Timeout de Gemini (segundos)",
  rag_top_k_chunks: "Chunks RAG recuperados (top-k)",
  rag_context_budget_chars: "Presupuesto de contexto RAG (caracteres)",
  system_prompt_pac: "System prompt PAC",
  history_max_entries: "Entradas de historial por usuario",
};

function SettingRow({
  setting,
  onSaved,
}: {
  setting: SystemSetting;
  onSaved: (updated: SystemSetting) => void;
}) {
  const [value, setValue] = useState(setting.value);
  const [saving, setSaving] = useState(false);
  const [flash, setFlash] = useState<FlashMessage>(null);

  const isDirty = value !== setting.value;
  const isTextarea = setting.key === "system_prompt_pac";

  async function handleSave() {
    setSaving(true);
    setFlash(null);
    try {
      const updated = await updateSetting(setting.key, value);
      onSaved(updated);
      setFlash({ kind: "success", text: "Guardado correctamente." });
    } catch (err) {
      setFlash({
        kind: "error",
        text: err instanceof Error ? err.message : "Error al guardar.",
      });
    } finally {
      setSaving(false);
    }
  }

  const inputClass =
    "w-full rounded-lg border border-border bg-bg px-3 py-1.5 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-accent/50";

  return (
    <div className="flex flex-col gap-2 rounded-xl border border-border bg-surface p-4">
      <div className="flex items-start justify-between gap-2">
        <div className="flex flex-col gap-0.5">
          <span className="text-sm font-semibold text-ink">
            {LABEL_MAP[setting.key] ?? setting.key}
          </span>
          {setting.description && (
            <span className="text-xs text-muted">{setting.description}</span>
          )}
        </div>
        <button
          type="button"
          disabled={!isDirty || saving}
          onClick={handleSave}
          className="inline-flex items-center gap-1.5 rounded-lg bg-accent px-3 py-1.5 text-xs font-medium text-white transition hover:bg-accent/90 disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
        >
          {saving ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Save className="h-3.5 w-3.5" />
          )}
          Guardar
        </button>
      </div>

      {isTextarea ? (
        <textarea
          className={`${inputClass} min-h-[200px] font-mono text-xs resize-y`}
          value={value}
          onChange={(e) => setValue(e.target.value)}
        />
      ) : FLOAT_KEYS.has(setting.key) ? (
        <input
          type="number"
          step="0.05"
          min="0"
          max="2"
          className={inputClass}
          value={value}
          onChange={(e) => setValue(e.target.value)}
        />
      ) : NUMERIC_KEYS.has(setting.key) ? (
        <input
          type="number"
          step="1"
          min="0"
          className={inputClass}
          value={value}
          onChange={(e) => setValue(e.target.value)}
        />
      ) : (
        <input
          type="text"
          className={inputClass}
          value={value}
          onChange={(e) => setValue(e.target.value)}
        />
      )}

      {flash && (
        <p
          className={`text-xs font-medium ${
            flash.kind === "success" ? "text-success" : "text-error"
          }`}
        >
          {flash.text}
        </p>
      )}
    </div>
  );
}

export function SettingsPanel() {
  const [settings, setSettings] = useState<SystemSetting[]>([]);
  const [loading, setLoading] = useState(true);
  const [flash, setFlash] = useState<FlashMessage>(null);
  const [resetting, setResetting] = useState(false);
  const [confirmReset, setConfirmReset] = useState(false);

  useEffect(() => {
    fetchSettings()
      .then(setSettings)
      .catch((err) =>
        setFlash({
          kind: "error",
          text: err instanceof Error ? err.message : "Error al cargar.",
        }),
      )
      .finally(() => setLoading(false));
  }, []);

  function handleSaved(updated: SystemSetting) {
    setSettings((prev) =>
      prev.map((s) => (s.key === updated.key ? updated : s)),
    );
  }

  async function handleReset() {
    if (!confirmReset) {
      setConfirmReset(true);
      return;
    }
    setResetting(true);
    setFlash(null);
    try {
      const updated = await resetSettings();
      setSettings(updated);
      setFlash({
        kind: "success",
        text: "Configuración restablecida a sus valores predeterminados.",
      });
    } catch (err) {
      setFlash({
        kind: "error",
        text:
          err instanceof Error ? err.message : "Error al restablecer.",
      });
    } finally {
      setResetting(false);
      setConfirmReset(false);
    }
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-lg font-semibold text-ink">Configuración del sistema</h1>
          <p className="text-sm text-muted mt-0.5">
            Parámetros de Gemini, RAG y comportamiento del asistente.
          </p>
        </div>
        <button
          type="button"
          onClick={handleReset}
          disabled={resetting || loading}
          className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-sm font-medium text-muted transition hover:text-error hover:border-error/40 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {resetting ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <RotateCcw className="h-4 w-4" />
          )}
          {confirmReset ? "¿Confirmar?" : "Restablecer todo"}
        </button>
      </div>

      {/* Global flash */}
      {flash && (
        <p
          className={`text-sm font-medium px-4 py-2 rounded-lg ${
            flash.kind === "success"
              ? "bg-success/10 text-success"
              : "bg-error/10 text-error"
          }`}
        >
          {flash.text}
        </p>
      )}

      {/* Content */}
      {loading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-muted" />
        </div>
      ) : (
        <div className="grid gap-4">
          {settings.map((s) => (
            <SettingRow key={s.key} setting={s} onSaved={handleSaved} />
          ))}
        </div>
      )}
    </div>
  );
}
