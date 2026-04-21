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

function getBaseUrl(): string {
  // In the browser, use a relative path so requests go through the
  // Next.js dev-server proxy (next.config.ts rewrites /api/* → api:8000).
  // Set NEXT_PUBLIC_API_BASE_URL only when you need a different absolute URL.
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
}

export async function sendChatMessage(
  prompt: string,
  config: ChatConfig,
  currentCode = "",
): Promise<ChatApiResponse> {
  const body = buildChatRequest(prompt, config, currentCode);
  const url = `${getBaseUrl()}/api/v1/chat/generate`;

  const response = await fetch(url, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    let detail = "Error al consultar el asistente.";
    try {
      const err = await response.json();
      if (typeof err.detail === "string") detail = err.detail;
    } catch {
      // keep default
    }
    throw new Error(detail);
  }

  return (await response.json()) as ChatApiResponse;
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
  const url = `${process.env.NEXT_PUBLIC_API_BASE_URL ?? ""}/api/v1/chat/history?limit=${limit}&offset=${offset}`;
  const response = await fetch(url, { credentials: "include" });
  if (!response.ok) return { items: [], total: 0 };
  return (await response.json()) as ChatHistoryListResponse;
}

export async function deleteChatHistoryItem(id: number): Promise<void> {
  const url = `${process.env.NEXT_PUBLIC_API_BASE_URL ?? ""}/api/v1/chat/history/${id}`;
  await fetch(url, { method: "DELETE", credentials: "include" });
}
