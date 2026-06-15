import { api } from "@/lib/api-client";
import type { ChatConfig } from "@/features/chat/chat-panel";

// ── Types matching the FastAPI schema ──────────────────────────────

export type ChatApiRequest = {
  prompt: string;
  robot_type: string;
  controller: string;
  io_profile: string;
  payload_kg: number;
  tool_number: number;
  max_speed_pct: number;
  hand_type: string;
  install_type: string;
  has_io_expansion: boolean;
  expansion_io_inputs: number;
  expansion_io_outputs: number;
  current_code: string;
};

export type ChatApiReference = {
  source_id: string;
  title: string;
  page: string;
};

export type ChatApiResponse = {
  summary: string;
  pac_code: string;
  references: ChatApiReference[];
};

// ── Helper: map frontend ChatConfig → API request body ────────────

export function buildChatRequest(
  prompt: string,
  config: ChatConfig,
  currentCode = "",
): ChatApiRequest {
  return {
    prompt,
    robot_type: config.robotModel,
    controller: config.controller,
    io_profile: `${config.ioInputs}I/${config.ioOutputs}O`,
    payload_kg: config.payloadKg,
    tool_number: config.toolNumber,
    max_speed_pct: config.maxSpeedPct,
    hand_type: config.handType,
    install_type: config.installType,
    has_io_expansion: config.hasIoExpansion,
    expansion_io_inputs: config.expansionIoInputs,
    expansion_io_outputs: config.expansionIoOutputs,
    current_code: currentCode,
  };
}

// ── API call ───────────────────────────────────────────────────────

export async function sendChatMessage(
  prompt: string,
  config: ChatConfig,
  currentCode = "",
): Promise<ChatApiResponse> {
  const body = buildChatRequest(prompt, config, currentCode);
  return api.post<ChatApiResponse>(
    "/api/v1/chat/generate",
    body,
    "Error al consultar el asistente.",
  );
}

// ── SSE streaming types ────────────────────────────────────────────

export type SSEChunkEvent = { type: "chunk"; content: string };
export type SSEDoneEvent = {
  type: "done";
  summary: string;
  pac_code: string;
  references: ChatApiReference[];
};
export type SSEErrorEvent = { type: "error"; message: string };
export type SSEEvent = SSEChunkEvent | SSEDoneEvent | SSEErrorEvent;

export type StreamChatCallbacks = {
  onFirstChunk: () => void;
  onChunk: (content: string) => void;
  onDone: (event: SSEDoneEvent) => void;
  onError: (event: SSEErrorEvent) => void;
};

export async function streamChatMessage(
  prompt: string,
  config: ChatConfig,
  currentCode = "",
  callbacks: StreamChatCallbacks,
): Promise<void> {
  const body = buildChatRequest(prompt, config, currentCode);

  const response = await fetch("/api/v1/chat/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    credentials: "include",
  });

  if (!response.ok || !response.body) {
    callbacks.onError({ type: "error", message: `Error HTTP ${response.status}` });
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let firstChunk = true;
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          const evt: SSEEvent = JSON.parse(line.slice(6));
          if (evt.type === "chunk") {
            if (firstChunk) {
              callbacks.onFirstChunk();
              firstChunk = false;
            }
            callbacks.onChunk(evt.content);
          } else if (evt.type === "done") {
            callbacks.onDone(evt);
          } else if (evt.type === "error") {
            callbacks.onError(evt);
          }
        } catch {
          // Ignore malformed SSE lines
        }
      }
    }
  }
}

// ── Chat history ───────────────────────────────────────────────────

export type ChatHistoryItem = {
  id: number;
  prompt: string;
  summary: string;
  pac_code: string;
  references: ChatApiReference[];
  robot_config: Record<string, unknown>;
  entry_type: "code" | "troubleshooting";
  created_at: string;
};

export type ChatHistoryListResponse = {
  items: ChatHistoryItem[];
  total: number;
};

export async function fetchChatHistory(limit = 50, offset = 0): Promise<ChatHistoryListResponse> {
  try {
    return await api.get<ChatHistoryListResponse>(
      `/api/v1/chat/history?limit=${limit}&offset=${offset}`,
    );
  } catch {
    return { items: [], total: 0 };
  }
}

export async function deleteChatHistoryItem(id: number): Promise<void> {
  await api.deleteVoid(`/api/v1/chat/history/${id}`);
}
