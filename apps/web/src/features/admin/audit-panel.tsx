"use client";

import { useEffect, useState } from "react";
import { ChevronLeft, ChevronRight, Loader2 } from "lucide-react";

import {
  fetchAuditLogs,
  type AuditLogEntry,
  type AuditLogFilters,
} from "@/lib/admin-audit";

type FlashMessage = { kind: "success" | "error"; text: string } | null;

const EVENT_TYPE_COLORS: Record<string, string> = {
  AUTH_LOGIN: "bg-green-100 text-green-800",
  AUTH_LOGOUT: "bg-slate-100 text-slate-700",
  AUTH_FAILED: "bg-red-100 text-red-800",
  ADMIN_USER_CREATED: "bg-blue-100 text-blue-800",
  ADMIN_USER_UPDATED: "bg-blue-100 text-blue-800",
  ADMIN_USER_TOGGLED: "bg-orange-100 text-orange-800",
  ADMIN_ROLE_CHANGED: "bg-purple-100 text-purple-800",
  MANUAL_UPLOADED: "bg-teal-100 text-teal-800",
  MANUAL_UPDATED: "bg-teal-100 text-teal-800",
  MANUAL_DELETED: "bg-red-100 text-red-800",
  INGESTION_STARTED: "bg-yellow-100 text-yellow-800",
  INGESTION_COMPLETED: "bg-green-100 text-green-800",
  INGESTION_FAILED: "bg-red-100 text-red-800",
  SETTING_UPDATED: "bg-indigo-100 text-indigo-800",
  SETTING_RESET: "bg-indigo-100 text-indigo-800",
  CHAT_QUERY: "bg-sky-100 text-sky-800",
  SYSTEM_ERROR: "bg-red-200 text-red-900",
};

function EventBadge({ eventType }: { eventType: string }) {
  const cls =
    EVENT_TYPE_COLORS[eventType] ?? "bg-gray-100 text-gray-700";
  return (
    <span className={`inline-block rounded px-2 py-0.5 text-xs font-semibold ${cls}`}>
      {eventType}
    </span>
  );
}

function MetadataCell({ data }: { data: Record<string, unknown> | null }) {
  const [open, setOpen] = useState(false);
  if (!data) return <span className="text-muted text-xs">—</span>;
  return (
    <div>
      <button
        onClick={() => setOpen((v) => !v)}
        className="text-xs text-accent underline"
      >
        {open ? "Ocultar" : "Ver datos"}
      </button>
      {open && (
        <pre className="mt-1 text-xs bg-surface rounded p-2 max-w-xs overflow-auto whitespace-pre-wrap border border-border">
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </div>
  );
}

const EVENT_TYPES = [
  "AUTH_LOGIN",
  "AUTH_LOGOUT",
  "AUTH_FAILED",
  "ADMIN_USER_CREATED",
  "ADMIN_USER_UPDATED",
  "ADMIN_USER_TOGGLED",
  "ADMIN_ROLE_CHANGED",
  "MANUAL_UPLOADED",
  "MANUAL_UPDATED",
  "MANUAL_DELETED",
  "INGESTION_STARTED",
  "INGESTION_COMPLETED",
  "INGESTION_FAILED",
  "SETTING_UPDATED",
  "SETTING_RESET",
  "CHAT_QUERY",
  "SYSTEM_ERROR",
];

export function AuditPanel() {
  const [entries, setEntries] = useState<AuditLogEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [flash, setFlash] = useState<FlashMessage>(null);

  const [filterEventType, setFilterEventType] = useState("");
  const [filterDateFrom, setFilterDateFrom] = useState("");
  const [filterDateTo, setFilterDateTo] = useState("");

  const PAGE_SIZE = 50;

  async function load(p: number, eventType: string, dateFrom: string, dateTo: string) {
    setLoading(true);
    setFlash(null);
    try {
      const filters: AuditLogFilters = { page: p, pageSize: PAGE_SIZE };
      if (eventType) filters.eventType = eventType;
      if (dateFrom) filters.dateFrom = dateFrom;
      if (dateTo) filters.dateTo = dateTo;
      const result = await fetchAuditLogs(filters);
      setEntries(result.items);
      setTotal(result.total);
      setPage(result.page);
      setPages(result.pages);
    } catch {
      setFlash({ kind: "error", text: "No fue posible cargar los eventos de auditoría." });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load(1, filterEventType, filterDateFrom, filterDateTo);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleFilter(e: React.FormEvent) {
    e.preventDefault();
    load(1, filterEventType, filterDateFrom, filterDateTo);
  }

  function handlePage(next: number) {
    load(next, filterEventType, filterDateFrom, filterDateTo);
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-ink">Auditoría</h2>

      {flash && (
        <div
          className={`rounded-lg px-4 py-3 text-sm ${
            flash.kind === "success"
              ? "bg-green-50 text-green-800 border border-green-200"
              : "bg-red-50 text-red-800 border border-red-200"
          }`}
        >
          {flash.text}
        </div>
      )}

      {/* Filters */}
      <form
        onSubmit={handleFilter}
        className="flex flex-wrap gap-3 items-end bg-surface border border-border rounded-lg p-4"
      >
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-muted">Tipo de evento</label>
          <select
            value={filterEventType}
            onChange={(e) => setFilterEventType(e.target.value)}
            className="text-sm border border-border rounded px-2 py-1.5 bg-bg-soft text-ink focus:outline-none"
          >
            <option value="">Todos</option>
            {EVENT_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-muted">Desde</label>
          <input
            type="datetime-local"
            value={filterDateFrom}
            onChange={(e) => setFilterDateFrom(e.target.value)}
            className="text-sm border border-border rounded px-2 py-1.5 bg-bg-soft text-ink focus:outline-none"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-muted">Hasta</label>
          <input
            type="datetime-local"
            value={filterDateTo}
            onChange={(e) => setFilterDateTo(e.target.value)}
            className="text-sm border border-border rounded px-2 py-1.5 bg-bg-soft text-ink focus:outline-none"
          />
        </div>
        <button
          type="submit"
          className="px-4 py-1.5 bg-accent text-white rounded text-sm font-medium hover:bg-accent/90 transition-colors"
        >
          Filtrar
        </button>
        <button
          type="button"
          onClick={() => {
            setFilterEventType("");
            setFilterDateFrom("");
            setFilterDateTo("");
            load(1, "", "", "");
          }}
          className="px-4 py-1.5 bg-surface border border-border text-ink rounded text-sm font-medium hover:bg-bg-soft transition-colors"
        >
          Limpiar
        </button>
      </form>

      {/* Table */}
      <div className="bg-surface border border-border rounded-lg overflow-hidden">
        <div className="flex items-center justify-between px-4 py-2 border-b border-border text-xs text-muted">
          <span>{total} eventos</span>
          {loading && <Loader2 className="h-4 w-4 animate-spin" />}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-muted border-b border-border bg-bg-soft">
                <th className="px-4 py-2 font-medium">Fecha</th>
                <th className="px-4 py-2 font-medium">Evento</th>
                <th className="px-4 py-2 font-medium">Actor</th>
                <th className="px-4 py-2 font-medium">Recurso</th>
                <th className="px-4 py-2 font-medium">Descripción</th>
                <th className="px-4 py-2 font-medium">Metadata</th>
                <th className="px-4 py-2 font-medium">IP</th>
              </tr>
            </thead>
            <tbody>
              {entries.length === 0 && !loading ? (
                <tr>
                  <td colSpan={7} className="text-center text-muted py-8 text-sm">
                    No hay eventos de auditoría.
                  </td>
                </tr>
              ) : (
                entries.map((entry) => (
                  <tr
                    key={entry.id}
                    className="border-b border-border hover:bg-bg-soft/50 transition-colors"
                  >
                    <td className="px-4 py-2 whitespace-nowrap text-xs text-muted">
                      {new Date(entry.createdAt).toLocaleString("es-MX")}
                    </td>
                    <td className="px-4 py-2">
                      <EventBadge eventType={entry.eventType} />
                    </td>
                    <td className="px-4 py-2 text-xs">
                      {entry.actorEmail ?? <span className="text-muted">—</span>}
                    </td>
                    <td className="px-4 py-2 text-xs">
                      {entry.resourceType ? (
                        <span>
                          {entry.resourceType}
                          {entry.resourceId ? ` #${entry.resourceId}` : ""}
                        </span>
                      ) : (
                        <span className="text-muted">—</span>
                      )}
                    </td>
                    <td className="px-4 py-2 text-xs max-w-xs truncate">
                      {entry.description}
                    </td>
                    <td className="px-4 py-2">
                      <MetadataCell data={entry.eventMetadata} />
                    </td>
                    <td className="px-4 py-2 text-xs text-muted whitespace-nowrap">
                      {entry.ipAddress ?? "—"}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {pages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-border text-sm">
            <span className="text-muted text-xs">
              Página {page} de {pages}
            </span>
            <div className="flex gap-2">
              <button
                disabled={page <= 1}
                onClick={() => handlePage(page - 1)}
                className="p-1 rounded border border-border hover:bg-bg-soft disabled:opacity-40 transition-colors"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <button
                disabled={page >= pages}
                onClick={() => handlePage(page + 1)}
                className="p-1 rounded border border-border hover:bg-bg-soft disabled:opacity-40 transition-colors"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
