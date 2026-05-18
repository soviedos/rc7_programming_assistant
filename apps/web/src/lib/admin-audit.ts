import { api } from "@/lib/api-client";

export type AuditLogEntry = {
  id: string;
  eventType: string;
  actorId: number | null;
  actorEmail: string | null;
  resourceType: string | null;
  resourceId: string | null;
  description: string;
  eventMetadata: Record<string, unknown> | null;
  ipAddress: string | null;
  createdAt: string;
};

type AuditLogApiEntry = {
  id: string;
  event_type: string;
  actor_id: number | null;
  actor_email: string | null;
  resource_type: string | null;
  resource_id: string | null;
  description: string;
  event_metadata: Record<string, unknown> | null;
  ip_address: string | null;
  created_at: string;
};

type AuditLogApiResponse = {
  items: AuditLogApiEntry[];
  total: number;
  page: number;
  pages: number;
};

export type AuditLogPage = {
  items: AuditLogEntry[];
  total: number;
  page: number;
  pages: number;
};

function normalizeEntry(raw: AuditLogApiEntry): AuditLogEntry {
  return {
    id: raw.id,
    eventType: raw.event_type,
    actorId: raw.actor_id,
    actorEmail: raw.actor_email,
    resourceType: raw.resource_type,
    resourceId: raw.resource_id,
    description: raw.description,
    eventMetadata: raw.event_metadata,
    ipAddress: raw.ip_address,
    createdAt: raw.created_at,
  };
}

export type AuditLogFilters = {
  eventType?: string;
  actorId?: number;
  resourceType?: string;
  dateFrom?: string;
  dateTo?: string;
  page?: number;
  pageSize?: number;
};

export async function fetchAuditLogs(
  filters: AuditLogFilters = {},
): Promise<AuditLogPage> {
  const params = new URLSearchParams();
  if (filters.eventType) params.set("event_type", filters.eventType);
  if (filters.actorId != null) params.set("actor_id", String(filters.actorId));
  if (filters.resourceType) params.set("resource_type", filters.resourceType);
  if (filters.dateFrom) params.set("date_from", filters.dateFrom);
  if (filters.dateTo) params.set("date_to", filters.dateTo);
  if (filters.page) params.set("page", String(filters.page));
  if (filters.pageSize) params.set("page_size", String(filters.pageSize));

  const qs = params.toString();
  const url = `/api/v1/admin/audit${qs ? `?${qs}` : ""}`;
  const raw = await api.get<AuditLogApiResponse>(
    url,
    "No fue posible cargar los eventos de auditoría.",
  );
  return {
    items: raw.items.map(normalizeEntry),
    total: raw.total,
    page: raw.page,
    pages: raw.pages,
  };
}
