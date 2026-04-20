"use client";

import { useState, useRef, useEffect, FormEvent } from "react";
import { Send, Paperclip, Copy, Check, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  code?: string;
  references?: string[];
  timestamp: Date;
};

type ChatConfig = {
  robotModel: string;
  controller: string;
};

const ROBOT_MODELS = [
  { value: "vp6242", label: "VP-6242" },
  { value: "vs6556", label: "VS-6556" },
  { value: "vm6083", label: "VM-6083" },
];

const CONTROLLERS = [
  { value: "rc7", label: "RC7" },
  { value: "rc8", label: "RC8" },
];

function CodeBlock({ code }: { code: string }) {
  const [copied, setCopied] = useState(false);

  function handleCopy() {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="mt-3 rounded-lg border border-border overflow-hidden">
      <div className="flex items-center justify-between px-3 py-1.5 bg-bg-soft border-b border-border">
        <span className="text-[11px] text-muted font-mono">PAC</span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 text-[11px] text-muted hover:text-ink transition-colors"
        >
          {copied ? <Check className="h-3 w-3 text-success" /> : <Copy className="h-3 w-3" />}
          {copied ? "Copiado" : "Copiar"}
        </button>
      </div>
      <pre className="p-3 text-xs font-mono leading-relaxed text-ink overflow-x-auto bg-bg">
        {code}
      </pre>
    </div>
  );
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";

  return (
    <div className={cn("flex gap-3 max-w-195", isUser ? "ml-auto flex-row-reverse" : "")}>
      <div className={cn(
        "shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-[11px] font-semibold mt-0.5",
        isUser
          ? "bg-accent/15 text-accent"
          : "bg-info/15 text-info"
      )}>
        {isUser ? "Tú" : "AI"}
      </div>

      <div className={cn("flex-1 min-w-0", isUser ? "text-right" : "")}>
        <div className={cn(
          "inline-block text-left rounded-xl px-4 py-3 text-sm leading-relaxed",
          isUser
            ? "bg-surface-strong text-ink"
            : "bg-surface text-ink"
        )}>
          <p className="whitespace-pre-wrap">{message.content}</p>
          {message.code && <CodeBlock code={message.code} />}
        </div>

        {message.references && message.references.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-2">
            {message.references.map((ref, i) => (
              <span key={i} className="text-[10px] px-2 py-0.5 rounded-full bg-info/10 text-info border border-info/20">
                {ref}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

const SAMPLE_MESSAGES: Message[] = [
  {
    id: "1",
    role: "user",
    content: "Genera una rutina PAC de Pick & Place con control de garra, approach seguro y una secuencia lista para copiar en Wincaps III.",
    timestamp: new Date(),
  },
  {
    id: "2",
    role: "assistant",
    content: "Preparé una secuencia orientada a RC7 para pick and place con TAKEARM, approach/depart, activación de mano y retorno a HOME. Está pensada para un flujo de producción estable y fácil de adaptar.",
    code: `PROGRAM PICK_AND_PLACE
  TAKEARM 1
  MOTOR ON
  SPEED 35
  APPROACH P, P[11], 80
  MOVE L, P_PICK
  HAND ON
  DLY 0.3
  DEPART 80
  MOVE P, P_SAFE
  APPROACH P, P[21], 100
  MOVE L, P_PLACE
  HAND OFF
  DLY 0.2
  DEPART 100
  MOVE P, P_HOME
END`,
    references: [
      "Programmer's Manual I · Motion",
      "PAC Library · Hand control",
    ],
    timestamp: new Date(),
  },
];

export function ChatPanel() {
  const [messages, setMessages] = useState<Message[]>(SAMPLE_MESSAGES);
  const [input, setInput] = useState("");
  const [config, setConfig] = useState<ChatConfig>({
    robotModel: "vp6242",
    controller: "rc7",
  });
  const [showConfig, setShowConfig] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text) return;

    const newMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: text,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, newMessage]);
    setInput("");
  }

  return (
    <div className="flex flex-col h-full">
      {/* Config bar */}
      <div className="flex items-center gap-2 px-4 py-2 border-b border-border bg-bg-soft/50">
        <button
          onClick={() => setShowConfig((s) => !s)}
          className="flex items-center gap-1.5 text-xs text-muted hover:text-ink transition-colors"
        >
          <span className="font-medium">
            {ROBOT_MODELS.find((m) => m.value === config.robotModel)?.label} · {CONTROLLERS.find((c) => c.value === config.controller)?.label}
          </span>
          <ChevronDown className={cn("h-3 w-3 transition-transform", showConfig && "rotate-180")} />
        </button>

        {showConfig && (
          <div className="flex items-center gap-2 ml-2">
            <select
              value={config.robotModel}
              onChange={(e) => setConfig((c) => ({ ...c, robotModel: e.target.value }))}
              className="text-xs bg-surface border border-border rounded-md px-2 py-1 text-ink cursor-pointer"
            >
              {ROBOT_MODELS.map((m) => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
            <select
              value={config.controller}
              onChange={(e) => setConfig((c) => ({ ...c, controller: e.target.value }))}
              className="text-xs bg-surface border border-border rounded-md px-2 py-1 text-ink cursor-pointer"
            >
              {CONTROLLERS.map((c) => (
                <option key={c.value} value={c.value}>{c.label}</option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        <div ref={endRef} />
      </div>

      {/* Composer */}
      <div className="border-t border-border bg-bg-soft/50 px-4 py-3">
        <form onSubmit={handleSubmit} className="flex items-end gap-2 max-w-195 mx-auto">
          <button
            type="button"
            className="shrink-0 p-2 rounded-lg text-muted hover:text-ink hover:bg-surface-hover transition-colors"
            aria-label="Adjuntar archivo"
          >
            <Paperclip className="h-4 w-4" />
          </button>

          <div className="flex-1 relative">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit(e);
                }
              }}
              placeholder="Describe la rutina PAC que necesitas…"
              rows={1}
              className="w-full resize-none rounded-xl bg-surface border border-border px-4 py-2.5 pr-10 text-sm text-ink placeholder:text-soft focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent/40 transition-colors"
            />
          </div>

          <button
            type="submit"
            disabled={!input.trim()}
            className="shrink-0 p-2.5 rounded-xl bg-accent text-white hover:bg-accent-hover disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            aria-label="Enviar"
          >
            <Send className="h-4 w-4" />
          </button>
        </form>
      </div>
    </div>
  );
}
