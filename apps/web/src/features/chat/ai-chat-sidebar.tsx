"use client";

import { useState, useRef, useEffect } from "react";
import { Bot, PanelRightClose, BookOpen, ChevronDown, ChevronUp, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

// ── Types ──────────────────────────────────────────────────────────

export type MessageReference = {
  sourceId: string; // traceability ID shown in the code, e.g. "S2"
  title: string;
  page: string;
};

export type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  code?: string;
  references?: MessageReference[];
  // Level-2 semantic advisories (each string already carries its line number).
  advisories?: string[];
  timestamp: Date;
  isError?: boolean;
  isStreaming?: boolean;
};

// ── Component ──────────────────────────────────────────────────────

import { History, Code2, Wrench, Trash2 } from "lucide-react";
import type { ChatHistoryItem } from "@/lib/chat";
import { deleteChatHistoryItem } from "@/lib/chat";

type AiChatSidebarProps = {
  isOpen: boolean;
  onToggle: () => void;
  messages: Message[];
  history: ChatHistoryItem[];
  onHistoryItemClick: (item: ChatHistoryItem) => void;
  onHistoryRefresh: () => void;
};

const MIN_WIDTH = 280;
const MAX_WIDTH = 640;
const DEFAULT_WIDTH = 320;

export function AiChatSidebar({
  isOpen,
  onToggle,
  messages,
  history,
  onHistoryItemClick,
  onHistoryRefresh,
}: AiChatSidebarProps) {
  const [historySectionOpen, setHistorySectionOpen] = useState(true);
  const [width, setWidth] = useState(DEFAULT_WIDTH);
  const endRef = useRef<HTMLDivElement>(null);
  const isDragging = useRef(false);
  const dragStartX = useRef(0);
  const dragStartWidth = useRef(0);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function handleResizeStart(e: React.MouseEvent) {
    e.preventDefault();
    isDragging.current = true;
    dragStartX.current = e.clientX;
    dragStartWidth.current = width;

    const onMouseMove = (ev: MouseEvent) => {
      if (!isDragging.current) return;
      // Dragging left = larger delta = wider sidebar
      const delta = dragStartX.current - ev.clientX;
      const newWidth = Math.max(MIN_WIDTH, Math.min(MAX_WIDTH, dragStartWidth.current + delta));
      setWidth(newWidth);
    };

    const onMouseUp = () => {
      isDragging.current = false;
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
    };

    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
  }

  return (
    <aside
      className={cn(
        "shrink-0 flex flex-col border-l border-border bg-bg transition-opacity duration-200 overflow-hidden relative",
        isOpen ? "" : "w-0 opacity-0 pointer-events-none"
      )}
      style={isOpen ? { width } : undefined}
    >
      {/* Drag handle */}
      {isOpen && (
        <div
          onMouseDown={handleResizeStart}
          className="absolute left-0 top-0 h-full w-1 cursor-col-resize hover:bg-accent/30 transition-colors z-10 group"
          aria-label="Redimensionar panel"
        >
          <div className="absolute inset-y-0 left-0 w-0.5 bg-transparent group-hover:bg-accent/40 transition-colors" />
        </div>
      )}
      <div className="flex flex-col h-full" style={{ width: isOpen ? width : DEFAULT_WIDTH }}>

        {/* Header */}
        <div className="flex items-center justify-between px-3 py-2.5 border-b border-border shrink-0">
          <div className="flex items-center gap-1.5">
            <Bot className="h-3.5 w-3.5 text-accent" />
            <span className="text-xs font-semibold text-ink">Interacciones IA</span>
            <span className="text-[10px] text-muted">· Fuentes</span>
          </div>
          <button
            onClick={onToggle}
            className="p-1 rounded-md text-muted hover:text-ink hover:bg-surface-hover transition-colors"
            aria-label="Cerrar panel"
          >
            <PanelRightClose className="h-3.5 w-3.5" />
          </button>
        </div>

        {/* ── History section ──────────────────────────────── */}
        <div className="border-b border-border shrink-0">
          <button
            onClick={() => setHistorySectionOpen((s) => !s)}
            className="w-full flex items-center justify-between px-3 py-2 text-left hover:bg-surface-hover transition-colors"
          >
            <div className="flex items-center gap-1.5">
              <History className="h-3.5 w-3.5 text-accent" />
              <span className="text-xs font-semibold text-ink">Historial</span>
              {history.length > 0 && (
                <span className="text-[10px] bg-accent/15 text-accent rounded-full px-1.5 py-0.5 font-medium">
                  {history.length}
                </span>
              )}
            </div>
            {historySectionOpen
              ? <ChevronUp className="h-3 w-3 text-muted" />
              : <ChevronDown className="h-3 w-3 text-muted" />}
          </button>

          {historySectionOpen && (
            <div className="pb-2 max-h-52 overflow-y-auto">
              {history.length === 0 ? (
                <p className="text-[10px] text-soft px-3 pb-2">Sin historial aún.</p>
              ) : (
                <ul className="space-y-0.5 px-2">
                  {history.map((item) => (
                    <li key={item.id} className="group flex items-start gap-1">
                      <button
                        onClick={() => onHistoryItemClick(item)}
                        className="flex-1 flex items-start gap-1.5 px-2 py-1.5 rounded-md text-left hover:bg-surface-hover transition-colors min-w-0"
                      >
                        {item.entry_type === "code" ? (
                          <Code2 className="h-3 w-3 text-accent shrink-0 mt-0.5" />
                        ) : (
                          <Wrench className="h-3 w-3 text-warning shrink-0 mt-0.5" />
                        )}
                        <div className="min-w-0">
                          <p className="text-[11px] text-ink leading-tight line-clamp-2">
                            {item.prompt}
                          </p>
                          <p className="text-[10px] text-soft mt-0.5">
                            {new Date(item.created_at).toLocaleDateString("es-MX", {
                              day: "2-digit",
                              month: "short",
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </p>
                        </div>
                      </button>
                      <button
                        onClick={async () => {
                          await deleteChatHistoryItem(item.id);
                          onHistoryRefresh();
                        }}
                        className="opacity-0 group-hover:opacity-100 p-1 mt-1 rounded text-soft hover:text-danger transition-all"
                        aria-label="Eliminar"
                      >
                        <Trash2 className="h-3 w-3" />
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-3 py-3 space-y-5">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-32 gap-2">
              <Bot className="h-6 w-6 text-muted/20" />
              <p className="text-[11px] text-soft text-center">Las interacciones y fuentes aparecerán aquí</p>
            </div>
          )}
          {messages.map((msg) => (
            <div key={msg.id}>
              {msg.role === "user" ? (
                /* User query — compact label */
                <div className="space-y-0.5">
                  <p className="text-[9px] font-semibold text-muted uppercase tracking-wide">Consulta</p>
                  <div className="rounded-lg px-3 py-2 bg-surface-strong text-ink text-[11px] leading-relaxed">
                    {msg.content}
                  </div>
                </div>
              ) : msg.isError ? (
                /* Error message */
                <div className="space-y-1 pl-1 border-l-2 border-destructive/40">
                  <div className="flex items-center gap-1.5 pl-2">
                    <Bot className="h-3 w-3 text-destructive shrink-0" />
                    <span className="text-[10px] text-destructive font-medium">Error</span>
                  </div>
                  <div className="pl-3 text-[11px] text-destructive/80 leading-relaxed">
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                  </div>
                </div>
              ) : (
                /* AI response — reasoning + references (or streaming state) */
                <div className="space-y-2 pl-1 border-l-2 border-accent/20">
                  <div className="flex items-center gap-1.5 pl-2">
                    <Bot className="h-3 w-3 text-accent shrink-0" />
                    <span className="text-[10px] text-accent font-medium">Gemini</span>
                  </div>

                  {msg.isStreaming ? (
                    <div className="pl-3 flex items-center gap-1.5 text-[11px] text-muted animate-pulse">
                      <span>Generando respuesta</span>
                      <span className="inline-flex gap-0.5">
                        <span className="h-1 w-1 rounded-full bg-accent animate-bounce [animation-delay:0ms]" />
                        <span className="h-1 w-1 rounded-full bg-accent animate-bounce [animation-delay:150ms]" />
                        <span className="h-1 w-1 rounded-full bg-accent animate-bounce [animation-delay:300ms]" />
                      </span>
                    </div>
                  ) : (
                    <div className="pl-3 text-[11px] text-ink leading-relaxed">
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                    </div>
                  )}

                  {/* Sources legend — decodes the ' fuente: SX tokens in the code.
                      Only the data in `references` is used (no model call). */}
                  {!msg.isStreaming && msg.references && msg.references.length > 0 && (
                    <div className="pl-3 pt-1 space-y-1.5">
                      <p className="text-[9px] text-muted uppercase tracking-wide font-semibold flex items-center gap-1">
                        <BookOpen className="h-2.5 w-2.5" />
                        Fuentes
                      </p>
                      {msg.references.map((ref) => (
                        <div
                          key={ref.sourceId}
                          className="text-[10px] px-2 py-1.5 rounded-md bg-info/8 border border-info/15 text-info flex items-baseline gap-1.5"
                        >
                          <span className="font-mono font-semibold shrink-0">
                            {ref.sourceId}
                          </span>
                          <span className="text-info/90">
                            — {ref.title}, pág. {ref.page}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Advisories — level-2 semantic warnings (read-only). Warning
                      style, distinct from the informative Fuentes block. */}
                  {!msg.isStreaming && msg.advisories && msg.advisories.length > 0 && (
                    <div className="pl-3 pt-1 space-y-1.5">
                      <p className="text-[9px] text-warning uppercase tracking-wide font-semibold flex items-center gap-1">
                        <AlertTriangle className="h-2.5 w-2.5" />
                        Advertencias
                      </p>
                      {msg.advisories.map((advisory, i) => (
                        <div
                          key={i}
                          className="text-[10px] px-2 py-1.5 rounded-md bg-warning/10 border border-warning/25 text-warning leading-relaxed"
                        >
                          {advisory}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
          <div ref={endRef} />
        </div>

      </div>
    </aside>
  );
}
