"use client";

import { useState } from "react";

import { ProtectedRoute } from "@/features/auth";
import { AppHeader } from "@/components/layout/app-header";
import { ChatPanel, HistorySidebar } from "@/features/chat";

export default function ChatPage() {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <ProtectedRoute allowedRoles={["admin", "user"]}>
      <div className="flex flex-col h-screen bg-bg">
        <AppHeader />
        <div className="flex flex-1 overflow-hidden relative">
          <HistorySidebar
            isOpen={sidebarOpen}
            onToggle={() => setSidebarOpen((s) => !s)}
          />
          <main className="flex-1 flex flex-col overflow-hidden">
            <ChatPanel />
          </main>
        </div>
      </div>
    </ProtectedRoute>
  );
}
