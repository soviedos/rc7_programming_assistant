import { Bot } from "lucide-react";

import { UserMenu } from "@/features/auth";

export function AppHeader() {
  return (
    <header className="flex items-center justify-between px-4 py-2.5 border-b border-border bg-bg-soft/80 backdrop-blur-sm">
      <div className="flex items-center gap-2.5">
        <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-accent/10">
          <Bot className="h-4.5 w-4.5 text-accent" />
        </div>
        <div className="flex flex-col">
          <h1 className="text-sm font-semibold text-ink leading-tight">
            RC7 Assistant
          </h1>
          <p className="text-[11px] text-muted leading-tight">
            DENSO Programming
          </p>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <UserMenu />
      </div>
    </header>
  );
}
