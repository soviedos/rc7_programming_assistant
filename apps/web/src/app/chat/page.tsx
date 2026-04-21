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
import { sendChatMessage, fetchChatHistory } from "@/lib/chat";
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

    try {
      const apiResp = await sendChatMessage(text, config, currentCode);

      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: apiResp.summary,
        code: apiResp.pac_code || undefined,
        references: apiResp.references.map((r) => ({
          manual: r.title,
          section: r.page,
        })),
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
      // Refresh history after successful response
      loadHistory();
    } catch (err) {
      const errorMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content:
          err instanceof Error
            ? err.message
            : "No se pudo obtener respuesta del asistente.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsSending(false);
    }
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
      code: item.pac_code || undefined,
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
