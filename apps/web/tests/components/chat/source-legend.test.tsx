import { render, screen } from "@testing-library/react";
import { beforeAll, describe, expect, it, vi } from "vitest";

import { AiChatSidebar, CanvasPanel, buildDefaultConfig } from "@/features/chat";
import type { Message } from "@/features/chat";

// ai-chat-sidebar imports deleteChatHistoryItem from the API client.
vi.mock("@/lib/chat", () => ({ deleteChatHistoryItem: vi.fn() }));

beforeAll(() => {
  // jsdom doesn't implement scrollIntoView (used in an effect on mount).
  window.HTMLElement.prototype.scrollIntoView = vi.fn();
});

const REFS = [
  { sourceId: "S1", title: "Programmer Manual", page: "12" },
  { sourceId: "S2", title: "Startup Guide", page: "45" },
];

function assistantMessage(overrides: Partial<Message> = {}): Message {
  return {
    id: "a1",
    role: "assistant",
    content: "Programa generado.",
    references: REFS,
    timestamp: new Date(),
    isStreaming: false,
    ...overrides,
  };
}

describe("AiChatSidebar — source legend", () => {
  function renderSidebar(messages: Message[]) {
    return render(
      <AiChatSidebar
        isOpen
        onToggle={() => {}}
        messages={messages}
        history={[]}
        onHistoryItemClick={() => {}}
        onHistoryRefresh={() => {}}
      />,
    );
  }

  it("renders a legend with 'SX — title, pág. page' per reference, ordered", () => {
    renderSidebar([assistantMessage()]);

    expect(screen.getByText("S1")).toBeInTheDocument();
    expect(screen.getByText("S2")).toBeInTheDocument();
    expect(screen.getByText(/— Programmer Manual, pág\. 12/)).toBeInTheDocument();
    expect(screen.getByText(/— Startup Guide, pág\. 45/)).toBeInTheDocument();
  });

  it("shows no legend when the message has no references", () => {
    renderSidebar([assistantMessage({ references: undefined })]);

    expect(screen.queryByText(/pág\./)).toBeNull();
    expect(screen.queryByText("S1")).toBeNull();
  });

  it("shows no legend while the message is still streaming", () => {
    renderSidebar([assistantMessage({ isStreaming: true, content: "" })]);
    expect(screen.queryByText(/pág\./)).toBeNull();
  });
});

describe("CanvasPanel code — ' fuente: SX highlighting", () => {
  function renderCanvas(messages: Message[]) {
    return render(
      <CanvasPanel
        mode="code"
        onModeChange={() => {}}
        messages={messages}
        onSend={() => {}}
        onClear={() => {}}
        config={buildDefaultConfig()}
        sidebarOpen
        onSidebarToggle={() => {}}
        chatOpen
        onChatToggle={() => {}}
      />,
    );
  }

  it("highlights each ' fuente: SX token and decodes it from references on hover", () => {
    const msg = assistantMessage({
      code: "PROGRAM p\n    MOVE P, P1    ' fuente: S2\n    GIVEARM\nEND",
      references: [{ sourceId: "S2", title: "Startup Guide", page: "45" }],
    });

    const { container } = renderCanvas([msg]);

    const token = container.querySelector('[data-source-id="S2"]');
    expect(token).not.toBeNull();
    expect(token?.textContent).toContain("' fuente: S2");
    // Tooltip is built only from `references` (no model call).
    expect(token?.getAttribute("title")).toBe("S2 — Startup Guide, pág. 45");
  });
});
