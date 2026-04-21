import { ROBOT_SPECS, CONTROLLERS, ROBOT_MODELS } from "./history-sidebar";
import type { HandType, InstallType } from "./history-sidebar";

// ── Config types ───────────────────────────────────────────────────

export type ChatConfig = {
  robotModel: string;
  controller: string;
  payloadKg: number;
  ioInputs: number;
  ioOutputs: number;
  hasIoExpansion: boolean;
  expansionIoInputs: number;
  expansionIoOutputs: number;
  handType: HandType;
  installType: InstallType;
  toolNumber: number;
  maxSpeedPct: number;
};

export function buildDefaultConfig(robotModel = "vp6242"): ChatConfig {
  const spec = ROBOT_SPECS[robotModel];
  return {
    robotModel,
    controller: "rc7",
    payloadKg: spec.maxPayloadKg,
    ioInputs: spec.ioInputOptions[0],
    ioOutputs: spec.ioOutputOptions[0],
    hasIoExpansion: false,
    expansionIoInputs: spec.expansionIoInputOptions[0],
    expansionIoOutputs: spec.expansionIoOutputOptions[0],
    handType: spec.handTypes[0],
    installType: spec.installTypes[0],
    toolNumber: 1,
    maxSpeedPct: 100,
  };
}

// Re-export for barrel imports
export { ROBOT_MODELS, CONTROLLERS, ROBOT_SPECS };

