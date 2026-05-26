"use client";

import { useState, useEffect, useCallback } from "react";

import { ProtectedRoute } from "@/features/auth";
import { AppHeader } from "@/components/layout/app-header";
import {
  HistorySidebar,
  buildDefaultConfig,
  AiChatSidebar,
  CanvasPanel,
} from "@/features/chat";
import type { ChatConfig, Message, WorkspaceMode } from "@/features/chat";
import { streamChatMessage, fetchChatHistory } from "@/lib/chat";
import type { ChatHistoryItem } from "@/lib/chat";

export default function ChatPage() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [chatOpen, setChatOpen] = useState(true);
  const [config, setConfig] = useState<ChatConfig>(buildDefaultConfig());
  const [mode, setMode] = useState<WorkspaceMode>("code");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isSending, setIsSending] = useState(false);
  const [history, setHistory] = useState<ChatHistoryItem[]>([]);

  const loadHistory = useCallback(async () => {
    const data = await fetchChatHistory();
    setHistory(data.items);
  }, []);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  async function handleSend(text: string, currentCode: string) {
    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: text,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsSending(true);

    const assistantId = (Date.now() + 1).toString();

    try {
      await streamChatMessage(text, config, currentCode, {
        onFirstChunk: () => {
          setIsSending(false);
          setMessages((prev) => [
            ...prev,
            {
              id: assistantId,
              role: "assistant",
              content: "",
              timestamp: new Date(),
              isStreaming: true,
            },
          ]);
        },
        onChunk: (_content) => {
          // Chunks are discarded; the final summary is shown on done
        },
        onDone: (evt) => {
          if (evt.pac_code) {
            setMode("code");
          }
          setMessages((prev) => {
            const hasPlaceholder = prev.some((m) => m.id === assistantId);
            const updatedMsg: Message = {
              id: assistantId,
              role: "assistant",
              isStreaming: false,
              content: evt.summary,
              code: evt.pac_code || undefined,
              references: evt.references.map((r) => ({
                manual: r.title,
                section: r.page,
              })),
              timestamp: new Date(),
            };
            return hasPlaceholder
              ? prev.map((m) => (m.id === assistantId ? updatedMsg : m))
              : [...prev, updatedMsg];
          });
          loadHistory();
        },
        onError: (evt) => {
          setMessages((prev) => {
            const hasPlaceholder = prev.some((m) => m.id === assistantId);
            const errorMsg: Message = {
              id: assistantId,
              role: "assistant",
              isError: true,
              content: evt.message || "No se pudo obtener respuesta del asistente.",
              timestamp: new Date(),
            };
            return hasPlaceholder
              ? prev.map((m) => (m.id === assistantId ? errorMsg : m))
              : [...prev, errorMsg];
          });
        },
      });
    } catch (err) {
      setMessages((prev) => {
        const hasPlaceholder = prev.some((m) => m.id === assistantId);
        const errorMsg: Message = {
          id: assistantId,
          role: "assistant",
          isError: true,
          content:
            err instanceof Error
              ? err.message
              : "No se pudo obtener respuesta del asistente.",
          timestamp: new Date(),
        };
        return hasPlaceholder
          ? prev.map((m) => (m.id === assistantId ? errorMsg : m))
          : [...prev, errorMsg];
      });
    } finally {
      setIsSending(false);
    }
  }

  function handleClear() {
    setMessages([]);
  }

  function handleHistoryItemClick(item: ChatHistoryItem) {
    const userMsg: Message = {
      id: `h-user-${item.id}`,
      role: "user",
      content: item.prompt,
      timestamp: new Date(item.created_at),
    };
    const assistantMsg: Message = {
      id: `h-assistant-${item.id}`,
      role: "assistant",
      content: item.summary,
      code: item.pac_code ?? undefined,
      references: item.references.map((r) => ({
        manual: r.title,
        section: r.page,
      })),
      timestamp: new Date(item.created_at),
    };
    setMessages([userMsg, assistantMsg]);
    // Switch to the appropriate mode
    setMode(item.entry_type === "code" ? "code" : "troubleshooting");
  }

  return (
    <ProtectedRoute allowedRoles={["admin", "user"]}>
      <div className="flex flex-col h-screen bg-bg">
        <AppHeader />
        <div className="flex flex-1 overflow-hidden">

          {/* Left: Robot configuration */}
          <HistorySidebar
            isOpen={sidebarOpen}
            onToggle={() => setSidebarOpen((s) => !s)}
            config={config}
            onConfigChange={setConfig}
          />

          {/* Center: Canvas (code / troubleshooting / training) + input bar */}
          <CanvasPanel
            mode={mode}
            onModeChange={setMode}
            messages={messages}
            onSend={handleSend}
            onClear={handleClear}
            isSending={isSending}
            config={config}
            sidebarOpen={sidebarOpen}
            onSidebarToggle={() => setSidebarOpen((s) => !s)}
            chatOpen={chatOpen}
            onChatToggle={() => setChatOpen((s) => !s)}
          />

          {/* Right: AI interactions, references, history */}
          <AiChatSidebar
            isOpen={chatOpen}
            onToggle={() => setChatOpen((s) => !s)}
            messages={messages}
            history={history}
            onHistoryItemClick={handleHistoryItemClick}
            onHistoryRefresh={loadHistory}
          />

        </div>
      </div>
    </ProtectedRoute>
  );
}
