"use client";

import { useState, useRef, FormEvent } from "react";
import {
  Code2,
  AlertTriangle,
  GraduationCap,
  Copy,
  Check,
  PanelLeft,
  PanelRight,
  Send,
  Loader2,
  SquarePen,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { ROBOT_SPECS, CONTROLLERS } from "./history-sidebar";
import type { ChatConfig } from "./chat-panel";
import type { Message } from "./ai-chat-sidebar";

// ── Types ──────────────────────────────────────────────────────────

export type WorkspaceMode = "code" | "troubleshooting" | "training";

const MODES: {
  value: WorkspaceMode;
  label: string;
  Icon: React.ComponentType<{ className?: string }>;
}[] = [
  { value: "code", label: "Código", Icon: Code2 },
  { value: "troubleshooting", label: "Troubleshooting", Icon: AlertTriangle },
  { value: "training", label: "Entrenamiento", Icon: GraduationCap },
];

// ── Code canvas ────────────────────────────────────────────────────

function CodeCanvas({ messages }: { messages: Message[] }) {
  const [copied, setCopied] = useState(false);

  const latestCode = [...messages]
    .reverse()
    .find((m) => m.role === "assistant" && m.code)?.code;

  function handleCopy() {
    if (!latestCode) return;
    navigator.clipboard.writeText(latestCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  if (!latestCode) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center space-y-3">
          <Code2 className="h-12 w-12 text-muted/20 mx-auto" />
          <p className="text-sm text-muted">El código generado aparecerá aquí</p>
          <p className="text-xs text-soft">
            Describe la rutina PAC que necesitas ↓
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-bg-soft/50 shrink-0">
        <span className="text-[11px] font-mono text-muted uppercase tracking-wide">
          PAC · RC7
        </span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 text-xs text-muted hover:text-ink transition-colors"
        >
          {copied ? (
            <Check className="h-3.5 w-3.5 text-success" />
          ) : (
            <Copy className="h-3.5 w-3.5" />
          )}
          {copied ? "Copiado" : "Copiar código"}
        </button>
      </div>
      {/* Code */}
      <div className="flex-1 overflow-auto bg-bg">
        <pre className="p-6 text-sm font-mono leading-relaxed text-ink whitespace-pre">
          {latestCode}
        </pre>
      </div>
    </div>
  );
}

// ── Troubleshooting canvas ─────────────────────────────────────────

function TroubleshootingCanvas({ messages }: { messages: Message[] }) {
  const hasResponses = messages.some((m) => m.role === "assistant");

  if (!hasResponses) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center space-y-3">
          <AlertTriangle className="h-12 w-12 text-muted/20 mx-auto" />
          <p className="text-sm text-muted">Describe el problema al asistente</p>
          <p className="text-xs text-soft">
            El diagnóstico paso a paso aparecerá aquí ↓
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-2xl mx-auto px-6 py-4 space-y-4">
        {messages.map((msg, i) => (
          <div key={msg.id} className="space-y-1">
            <p className="text-[10px] font-semibold text-muted uppercase tracking-wide">
              {msg.role === "user"
                ? "Problema reportado"
                : `Diagnóstico ${Math.floor(i / 2) + 1}`}
            </p>
            <div
              className={cn(
                "rounded-lg p-3.5 text-sm leading-relaxed border border-border",
                msg.role === "user"
                  ? "bg-surface text-muted"
                  : "bg-surface text-ink"
              )}
            >
              {msg.content}
            </div>

            {/* Sources */}
            {msg.references && msg.references.length > 0 && (
              <div className="flex flex-wrap gap-1.5 pt-1">
                {msg.references.map((ref, j) => (
                  <span
                    key={j}
                    className="text-[10px] px-2 py-0.5 rounded-full bg-info/8 border border-info/15 text-info"
                  >
                    {ref.manual}
                    {ref.section && ` · ${ref.section}`}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Training canvas ────────────────────────────────────────────────

function TrainingCanvas() {
  return (
    <div className="flex-1 flex items-center justify-center">
      <div className="text-center space-y-4 max-w-sm">
        <GraduationCap className="h-12 w-12 text-muted/20 mx-auto" />
        <div className="space-y-2">
          <p className="text-sm text-ink font-medium">Módulo de entrenamiento</p>
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-warning/10 text-warning border border-warning/20">
            <span className="h-1.5 w-1.5 rounded-full bg-warning animate-pulse" />
            En desarrollo
          </span>
        </div>
        <p className="text-xs text-soft leading-relaxed">
          Próximamente: módulos de aprendizaje guiado, ejercicios de código PAC
          y referencia rápida de comandos RC7.
        </p>
      </div>
    </div>
  );
}

// ── Canvas panel ───────────────────────────────────────────────────

type CanvasPanelProps = {
  mode: WorkspaceMode;
  onModeChange: (m: WorkspaceMode) => void;
  messages: Message[];
  onSend: (text: string, currentCode: string) => void;
  onClear: () => void;
  isSending?: boolean;
  config: ChatConfig;
  sidebarOpen: boolean;
  onSidebarToggle: () => void;
  chatOpen: boolean;
  onChatToggle: () => void;
};

const PLACEHOLDERS: Record<WorkspaceMode, string> = {
  code: "Describe la rutina PAC que necesitas…",
  troubleshooting: "Describe el problema o error del robot…",
  training: "Módulo en desarrollo",
};

export function CanvasPanel({
  mode,
  onModeChange,
  messages,
  onSend,
  onClear,
  isSending = false,
  config,
  sidebarOpen,
  onSidebarToggle,
  chatOpen,
  onChatToggle,
}: CanvasPanelProps) {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const spec = ROBOT_SPECS[config.robotModel];

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || mode === "training" || isSending) return;
    const currentCode = [...messages].reverse().find((m) => m.role === "assistant" && m.code)?.code ?? "";
    onSend(text, currentCode);
    setInput("");
    textareaRef.current?.focus();
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden min-w-0">

      {/* Context bar */}
      <div className="flex items-center gap-x-3 flex-wrap px-4 py-1.5 border-b border-border bg-bg-soft/50 text-[11px] text-muted shrink-0">
        {!sidebarOpen && (
          <button
            onClick={onSidebarToggle}
            className="shrink-0 p-1 rounded-md text-muted hover:text-ink hover:bg-surface-hover transition-colors"
            aria-label="Mostrar configuración"
          >
            <PanelLeft className="h-4 w-4" />
          </button>
        )}

        <span className="font-semibold text-ink">{spec?.label ?? config.robotModel}</span>
        <span>·</span>
        <span>{CONTROLLERS.find((c) => c.value === config.controller)?.label}</span>

        {spec && (
          <>
            <span>·</span>
            <span>{spec.axes} ejes</span>
            <span>·</span>
            <span>Carga máx. {spec.maxPayloadKg} kg</span>
            <span>·</span>
            <span>Alcance {spec.reachMm} mm</span>
          </>
        )}

        <span>·</span>
        <span>{config.payloadKg} kg manip.</span>
        <span>·</span>
        <span>
          {config.ioInputs}I / {config.ioOutputs}O
          {config.hasIoExpansion
            ? ` +${config.expansionIoInputs}I/${config.expansionIoOutputs}O exp.`
            : ""}
        </span>
        <span>·</span>
        <span>Tool {config.toolNumber}</span>
        <span>·</span>
        <span>{config.maxSpeedPct}% vel.</span>

        {!chatOpen && (
          <button
            onClick={onChatToggle}
            className="ml-auto shrink-0 p-1 rounded-md text-muted hover:text-ink hover:bg-surface-hover transition-colors"
            aria-label="Mostrar asistente"
          >
            <PanelRight className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Mode tabs */}
      <div className="flex items-center border-b border-border bg-bg-soft/20 px-2 shrink-0">
        {MODES.map(({ value, label, Icon }) => (
          <button
            key={value}
            onClick={() => onModeChange(value)}
            className={cn(
              "flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors",
              mode === value
                ? "border-accent text-accent"
                : "border-transparent text-muted hover:text-ink"
            )}
          >
            <Icon className="h-3.5 w-3.5" />
            {label}
          </button>
        ))}
        <button
          onClick={onClear}
          disabled={messages.length === 0 || isSending}
          className="ml-auto flex items-center gap-1.5 px-3 py-1.5 text-xs text-muted hover:text-ink hover:bg-surface-hover rounded-md transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          aria-label="Nueva consulta"
        >
          <SquarePen className="h-3.5 w-3.5" />
          Nueva consulta
        </button>
      </div>

      {/* Canvas content */}
      {mode === "code" && <CodeCanvas messages={messages} />}
      {mode === "troubleshooting" && <TroubleshootingCanvas messages={messages} />}
      {mode === "training" && <TrainingCanvas />}

      {/* Query input bar */}
      <div className="border-t border-border bg-bg-soft/40 px-4 py-3 shrink-0">
        <form onSubmit={handleSubmit} className="flex items-end gap-2">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e as unknown as FormEvent);
              }
            }}
            disabled={mode === "training" || isSending}
            placeholder={isSending ? "Consultando a Gemini…" : PLACEHOLDERS[mode]}
            rows={2}
            className="flex-1 resize-none rounded-xl bg-surface border border-border px-4 py-2.5 text-sm text-ink placeholder:text-soft focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent/40 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          />
          <button
            type="submit"
            disabled={!input.trim() || mode === "training" || isSending}
            className="shrink-0 p-2.5 rounded-xl bg-accent text-white hover:bg-accent-hover disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            aria-label="Enviar consulta"
          >
            {isSending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
