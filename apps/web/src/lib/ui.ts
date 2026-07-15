/** Types shared across UI panels. */

/** Inline banner shown after an action succeeds or fails. `null` = nothing shown. */
export type FlashMessage = { kind: "success" | "error"; text: string } | null;
