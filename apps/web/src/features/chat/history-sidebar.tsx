"use client";

import { useState } from "react";
import {
  PanelLeftClose,
  Bot,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { ChatConfig } from "./chat-panel";

// ── Robot catalogue ────────────────────────────────────────────────

export type HandType = "pneumatic_single" | "pneumatic_double" | "electric" | "none";
export type InstallType = "floor" | "ceiling" | "wall";

type RobotSpec = {
  label: string;
  axes: number;
  maxPayloadKg: number;
  reachMm: number;
  payloadOptions: number[];
  ioInputOptions: number[];
  ioOutputOptions: number[];
  expansionIoInputOptions: number[];
  expansionIoOutputOptions: number[];
  handTypes: HandType[];
  installTypes: InstallType[];
  toolCount: number;
  maxSpeedPct: number;
};

export const ROBOT_SPECS: Record<string, RobotSpec> = {
  vp6242: {
    label: "VP-6242",
    axes: 6,
    maxPayloadKg: 2,
    reachMm: 420,
    payloadOptions: [0.5, 1.0, 1.5, 2.0],
    ioInputOptions: [16, 32],
    ioOutputOptions: [16, 32],
    expansionIoInputOptions: [16, 32],
    expansionIoOutputOptions: [16, 32],
    handTypes: ["pneumatic_single", "pneumatic_double", "electric", "none"],
    installTypes: ["floor", "ceiling", "wall"],
    toolCount: 8,
    maxSpeedPct: 100,
  },
  vs6556: {
    label: "VS-6556",
    axes: 6,
    maxPayloadKg: 6,
    reachMm: 556,
    payloadOptions: [1.0, 2.0, 4.0, 6.0],
    ioInputOptions: [16, 32],
    ioOutputOptions: [16, 32],
    expansionIoInputOptions: [16, 32],
    expansionIoOutputOptions: [16, 32],
    handTypes: ["pneumatic_single", "pneumatic_double", "electric", "none"],
    installTypes: ["floor", "ceiling"],
    toolCount: 8,
    maxSpeedPct: 100,
  },
  vm6083: {
    label: "VM-6083",
    axes: 6,
    maxPayloadKg: 20,
    reachMm: 830,
    payloadOptions: [5.0, 10.0, 15.0, 20.0],
    ioInputOptions: [32, 64],
    ioOutputOptions: [32, 64],
    expansionIoInputOptions: [32, 64],
    expansionIoOutputOptions: [32, 64],
    handTypes: ["pneumatic_double", "electric", "none"],
    installTypes: ["floor"],
    toolCount: 8,
    maxSpeedPct: 100,
  },
  vs087a3: {
    label: "VS-087",
    axes: 6,
    maxPayloadKg: 7,
    reachMm: 870,
    payloadOptions: [1.0, 3.0, 5.0, 7.0],
    ioInputOptions: [16, 32],
    ioOutputOptions: [16, 32],
    expansionIoInputOptions: [16, 32],
    expansionIoOutputOptions: [16, 32],
    handTypes: ["pneumatic_single", "pneumatic_double", "none"],
    installTypes: ["floor", "ceiling", "wall"],
    toolCount: 8,
    maxSpeedPct: 100,
  },
};

export const ROBOT_MODELS = Object.entries(ROBOT_SPECS).map(([value, spec]) => ({
  value,
  label: spec.label,
}));

export const CONTROLLERS = [
  { value: "rc7", label: "RC7" },
  { value: "rc8", label: "RC8" },
];

const HAND_TYPE_LABELS: Record<HandType, string> = {
  pneumatic_single: "Neumática simple",
  pneumatic_double: "Neumática doble",
  electric: "Eléctrica",
  none: "Sin mano",
};

const INSTALL_TYPE_LABELS: Record<InstallType, string> = {
  floor: "Piso",
  ceiling: "Techo",
  wall: "Pared",
};

// ── Props ──────────────────────────────────────────────────────────

type HistorySidebarProps = {
  isOpen: boolean;
  onToggle: () => void;
  config: ChatConfig;
  onConfigChange: (config: ChatConfig) => void;
};

// ── Component ─────────────────────────────────────────────────────

export function HistorySidebar({ isOpen, onToggle, config, onConfigChange }: HistorySidebarProps) {
  const [robotSectionOpen, setRobotSectionOpen] = useState(true);

  const spec = ROBOT_SPECS[config.robotModel];

  function set<K extends keyof ChatConfig>(key: K, value: ChatConfig[K]) {
    const next = { ...config, [key]: value };
    // Reset robot-dependent fields when model changes
    if (key === "robotModel") {
      const newSpec = ROBOT_SPECS[value as string];
      next.payloadKg = newSpec.maxPayloadKg;
      next.ioInputs = newSpec.ioInputOptions[0];
      next.ioOutputs = newSpec.ioOutputOptions[0];
      next.hasIoExpansion = false;
      next.expansionIoInputs = newSpec.expansionIoInputOptions[0];
      next.expansionIoOutputs = newSpec.expansionIoOutputOptions[0];
      next.handType = newSpec.handTypes[0];
      next.installType = newSpec.installTypes[0];
      next.toolNumber = 1;
      next.maxSpeedPct = 100;
    }
    onConfigChange(next);
  }

  return (
    <>
      {/* Sidebar */}
      <aside className={cn(
        "shrink-0 border-r border-border bg-bg-soft/50 transition-all duration-200 overflow-hidden",
        isOpen ? "w-64" : "w-0"
      )}>
        <div className="flex flex-col h-full w-64 overflow-y-auto">

          {/* ── Robot config section ──────────────────────────────── */}
          <div className="border-b border-border">
            <button
              onClick={() => setRobotSectionOpen((s) => !s)}
              className="w-full flex items-center justify-between px-3 py-2.5 text-left hover:bg-surface-hover transition-colors"
            >
              <div className="flex items-center gap-1.5">
                <Bot className="h-3.5 w-3.5 text-accent" />
                <span className="text-xs font-semibold text-ink">Configuración de robot</span>
              </div>
              {robotSectionOpen
                ? <ChevronUp className="h-3 w-3 text-muted" />
                : <ChevronDown className="h-3 w-3 text-muted" />}
            </button>

            {robotSectionOpen && (
              <div className="px-3 pb-3 space-y-3">

                {/* Robot model */}
                <div className="space-y-1">
                  <label className="text-[10px] font-medium text-muted uppercase tracking-wide">
                    Modelo de robot
                  </label>
                  <select
                    value={config.robotModel}
                    onChange={(e) => set("robotModel", e.target.value)}
                    className="w-full text-xs bg-surface border border-border rounded-md px-2 py-1.5 text-ink cursor-pointer focus:outline-none focus:ring-1 focus:ring-accent/40"
                  >
                    {ROBOT_MODELS.map((m) => (
                      <option key={m.value} value={m.value}>{m.label}</option>
                    ))}
                  </select>
                </div>

                {/* Controladora */}
                <div className="space-y-1">
                  <label className="text-[10px] font-medium text-muted uppercase tracking-wide">
                    Controladora
                  </label>
                  <select
                    value={config.controller}
                    onChange={(e) => set("controller", e.target.value)}
                    className="w-full text-xs bg-surface border border-border rounded-md px-2 py-1.5 text-ink cursor-pointer focus:outline-none focus:ring-1 focus:ring-accent/40"
                  >
                    {CONTROLLERS.map((c) => (
                      <option key={c.value} value={c.value}>{c.label}</option>
                    ))}
                  </select>
                </div>

                {/* ── Robot-specific options ──────────────────────── */}
                <p className="text-[10px] font-semibold text-muted uppercase tracking-wide pt-1">
                  Opciones de programación
                </p>

                {/* Payload */}
                <div className="space-y-1">
                  <label className="text-[10px] text-muted">
                    Peso manipulador (kg)
                  </label>
                  <input
                    type="number"
                    min={0.01}
                    max={spec.maxPayloadKg}
                    step={0.01}
                    value={config.payloadKg}
                    onChange={(e) => {
                      const val = parseFloat(e.target.value);
                      if (!isNaN(val) && val > 0 && val <= spec.maxPayloadKg) {
                        set("payloadKg", val);
                      }
                    }}
                    className="w-full text-xs bg-surface border border-border rounded-md px-2 py-1.5 text-ink focus:outline-none focus:ring-1 focus:ring-accent/40"
                  />
                  <p className="text-[10px] text-soft">Máx. {spec.maxPayloadKg} kg</p>
                </div>

                {/* Hand type */}
                <div className="space-y-1">
                  <label className="text-[10px] text-muted">
                    Tipo de manipulador
                  </label>
                  <select
                    value={config.handType}
                    onChange={(e) => set("handType", e.target.value as HandType)}
                    className="w-full text-xs bg-surface border border-border rounded-md px-2 py-1.5 text-ink cursor-pointer focus:outline-none focus:ring-1 focus:ring-accent/40"
                  >
                    {spec.handTypes.map((h) => (
                      <option key={h} value={h}>{HAND_TYPE_LABELS[h]}</option>
                    ))}
                  </select>
                </div>

                {/* IO inputs */}
                <div className="space-y-1">
                  <label className="text-[10px] text-muted">
                    Entradas digitales (IO)
                  </label>
                  <select
                    value={config.ioInputs}
                    onChange={(e) => set("ioInputs", parseInt(e.target.value))}
                    className="w-full text-xs bg-surface border border-border rounded-md px-2 py-1.5 text-ink cursor-pointer focus:outline-none focus:ring-1 focus:ring-accent/40"
                  >
                    {spec.ioInputOptions.map((n) => (
                      <option key={n} value={n}>{n} entradas</option>
                    ))}
                  </select>
                </div>

                {/* IO outputs */}
                <div className="space-y-1">
                  <label className="text-[10px] text-muted">
                    Salidas digitales (IO)
                  </label>
                  <select
                    value={config.ioOutputs}
                    onChange={(e) => set("ioOutputs", parseInt(e.target.value))}
                    className="w-full text-xs bg-surface border border-border rounded-md px-2 py-1.5 text-ink cursor-pointer focus:outline-none focus:ring-1 focus:ring-accent/40"
                  >
                    {spec.ioOutputOptions.map((n) => (
                      <option key={n} value={n}>{n} salidas</option>
                    ))}
                  </select>
                </div>

                {/* IO expansion card */}
                <div className="space-y-1">
                  <label className="text-[10px] text-muted">Tarjeta de expansión IO</label>
                  <div className="flex rounded-md border border-border overflow-hidden text-xs">
                    <button
                      type="button"
                      onClick={() => set("hasIoExpansion", false)}
                      className={cn(
                        "flex-1 py-1.5 transition-colors",
                        !config.hasIoExpansion
                          ? "bg-accent text-white font-medium"
                          : "bg-surface text-muted hover:bg-surface-hover"
                      )}
                    >
                      No
                    </button>
                    <button
                      type="button"
                      onClick={() => set("hasIoExpansion", true)}
                      className={cn(
                        "flex-1 py-1.5 transition-colors",
                        config.hasIoExpansion
                          ? "bg-accent text-white font-medium"
                          : "bg-surface text-muted hover:bg-surface-hover"
                      )}
                    >
                      Sí
                    </button>
                  </div>
                </div>

                {/* Expansion IO selects — shown only when expansion card is present */}
                {config.hasIoExpansion && (
                  <>
                    <div className="space-y-1">
                      <label className="text-[10px] text-muted">
                        Entradas expansión (IO)
                      </label>
                      <select
                        value={config.expansionIoInputs}
                        onChange={(e) => set("expansionIoInputs", parseInt(e.target.value))}
                        className="w-full text-xs bg-surface border border-border rounded-md px-2 py-1.5 text-ink cursor-pointer focus:outline-none focus:ring-1 focus:ring-accent/40"
                      >
                        {spec.expansionIoInputOptions.map((n) => (
                          <option key={n} value={n}>{n} entradas</option>
                        ))}
                      </select>
                    </div>

                    <div className="space-y-1">
                      <label className="text-[10px] text-muted">
                        Salidas expansión (IO)
                      </label>
                      <select
                        value={config.expansionIoOutputs}
                        onChange={(e) => set("expansionIoOutputs", parseInt(e.target.value))}
                        className="w-full text-xs bg-surface border border-border rounded-md px-2 py-1.5 text-ink cursor-pointer focus:outline-none focus:ring-1 focus:ring-accent/40"
                      >
                        {spec.expansionIoOutputOptions.map((n) => (
                          <option key={n} value={n}>{n} salidas</option>
                        ))}
                      </select>
                    </div>
                  </>
                )}

                {/* Installation type */}
                <div className="space-y-1">
                  <label className="text-[10px] text-muted">
                    Tipo de instalación
                  </label>
                  <select
                    value={config.installType}
                    onChange={(e) => set("installType", e.target.value as InstallType)}
                    className="w-full text-xs bg-surface border border-border rounded-md px-2 py-1.5 text-ink cursor-pointer focus:outline-none focus:ring-1 focus:ring-accent/40"
                  >
                    {spec.installTypes.map((t) => (
                      <option key={t} value={t}>{INSTALL_TYPE_LABELS[t]}</option>
                    ))}
                  </select>
                </div>

                {/* Tool number */}
                <div className="space-y-1">
                  <label className="text-[10px] text-muted">
                    Número de herramienta activa
                  </label>
                  <select
                    value={config.toolNumber}
                    onChange={(e) => set("toolNumber", parseInt(e.target.value))}
                    className="w-full text-xs bg-surface border border-border rounded-md px-2 py-1.5 text-ink cursor-pointer focus:outline-none focus:ring-1 focus:ring-accent/40"
                  >
                    {Array.from({ length: spec.toolCount }, (_, i) => i + 1).map((n) => (
                      <option key={n} value={n}>Tool {n}</option>
                    ))}
                  </select>
                </div>

                {/* Max speed */}
                <div className="space-y-1">
                  <label className="text-[10px] text-muted">
                    Velocidad máxima permitida
                  </label>
                  <div className="flex items-center gap-2">
                    <input
                      type="range"
                      min={10}
                      max={spec.maxSpeedPct}
                      step={5}
                      value={config.maxSpeedPct}
                      onChange={(e) => set("maxSpeedPct", parseInt(e.target.value))}
                      className="flex-1 h-1.5 accent-accent cursor-pointer"
                    />
                    <span className="text-[10px] text-ink font-medium w-8 text-right">
                      {config.maxSpeedPct}%
                    </span>
                  </div>
                </div>

              </div>
            )}
          </div>

          {/* ── Collapse button ───────────────────────────────────── */}
          <div className="flex justify-end px-2 py-1.5 border-t border-border">
            <button
              onClick={onToggle}
              className="p-1 rounded-md text-muted hover:text-ink hover:bg-surface-hover transition-colors"
              aria-label="Ocultar panel"
            >
              <PanelLeftClose className="h-3.5 w-3.5" />
            </button>
          </div>

        </div>
      </aside>
    </>
  );
}
