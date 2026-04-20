"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BookOpenText, ShieldCheck, Users } from "lucide-react";

import { cn } from "@/lib/utils";

const LINKS = [
  { href: "/admin/manuals", label: "Manuales", icon: BookOpenText },
  { href: "/admin/users", label: "Usuarios", icon: Users },
  { href: "/admin/roles", label: "Roles", icon: ShieldCheck },
];

export function AdminNav() {
  const pathname = usePathname();

  return (
    <aside className="w-full md:w-64 border-b md:border-b-0 md:border-r border-border bg-bg-soft shrink-0">
      <div className="px-4 pt-4 pb-2 md:pb-3">
        <h2 className="text-xs font-semibold tracking-wide text-muted uppercase">
          Admin
        </h2>
      </div>
      <ul className="px-3 pb-3 flex md:flex-col items-center md:items-stretch gap-2 overflow-x-auto">
        {LINKS.map((link) => {
          const active = pathname === link.href;
          const Icon = link.icon;

          return (
            <li key={link.href}>
              <Link
                href={link.href}
                className={cn(
                  "inline-flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium border transition-colors whitespace-nowrap",
                  active
                    ? "bg-accent/10 text-accent border-accent/20"
                    : "text-muted border-transparent hover:text-ink hover:bg-surface",
                )}
              >
                <Icon className="h-4 w-4" />
                {link.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </aside>
  );
}
