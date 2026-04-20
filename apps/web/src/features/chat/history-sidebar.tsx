"use client";

import { useState } from "react";
import { MessageSquare, Plus, PanelLeftClose, PanelLeft } from "lucide-react";
import { cn } from "@/lib/utils";

type Conversation = {
  id: string;
  title: string;
  updatedAt: string;
};

const SAMPLE_CONVERSATIONS: Conversation[] = [
  { id: "1", title: "Pick and place base", updatedAt: "hace 5 min" },
  { id: "2", title: "Alarm recovery draft", updatedAt: "hace 18 min" },
  { id: "3", title: "IO mapping review", updatedAt: "ayer" },
];

type HistorySidebarProps = {
  isOpen: boolean;
  onToggle: () => void;
};

export function HistorySidebar({ isOpen, onToggle }: HistorySidebarProps) {
  const [conversations] = useState<Conversation[]>(SAMPLE_CONVERSATIONS);
  const [activeId, setActiveId] = useState<string>("1");

  return (
    <>
      {/* Toggle button when collapsed */}
      {!isOpen && (
        <button
          onClick={onToggle}
          className="absolute left-2 top-2 z-10 p-1.5 rounded-md text-muted hover:text-ink hover:bg-surface-hover transition-colors"
          aria-label="Mostrar historial"
        >
          <PanelLeft className="h-4 w-4" />
        </button>
      )}

      {/* Sidebar */}
      <aside className={cn(
        "shrink-0 border-r border-border bg-bg-soft/50 transition-all duration-200 overflow-hidden",
        isOpen ? "w-60" : "w-0"
      )}>
        <div className="flex flex-col h-full w-60">
          {/* Header */}
          <div className="flex items-center justify-between px-3 py-2.5 border-b border-border">
            <span className="text-xs font-medium text-muted">Historial</span>
            <div className="flex items-center gap-1">
              <button
                className="p-1 rounded-md text-muted hover:text-ink hover:bg-surface-hover transition-colors"
                aria-label="Nueva conversación"
              >
                <Plus className="h-3.5 w-3.5" />
              </button>
              <button
                onClick={onToggle}
                className="p-1 rounded-md text-muted hover:text-ink hover:bg-surface-hover transition-colors"
                aria-label="Ocultar historial"
              >
                <PanelLeftClose className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>

          {/* List */}
          <div className="flex-1 overflow-y-auto py-1">
            {conversations.map((conv) => (
              <button
                key={conv.id}
                onClick={() => setActiveId(conv.id)}
                className={cn(
                  "w-full text-left px-3 py-2 flex items-start gap-2 hover:bg-surface-hover transition-colors",
                  activeId === conv.id && "bg-surface"
                )}
              >
                <MessageSquare className="h-3.5 w-3.5 text-muted mt-0.5 shrink-0" />
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-ink truncate">{conv.title}</p>
                  <p className="text-[10px] text-soft">{conv.updatedAt}</p>
                </div>
              </button>
            ))}
          </div>
        </div>
      </aside>
    </>
  );
}
