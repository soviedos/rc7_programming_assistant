type ApiValidationDetail = {
  loc?: Array<string | number>;
  msg?: string;
  type?: string;
};

type ApiErrorBody = {
  detail?: string | ApiValidationDetail[];
};

function getBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
}

function normalizeErrorMessage(
  detail: ApiErrorBody["detail"],
  fallback: string,
): string {
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((entry) => entry.msg?.trim())
      .filter((msg): msg is string => Boolean(msg));

    if (messages.length > 0) {
      return messages.join(" ");
    }
  }

  return fallback;
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  fallbackError: string = "Error en la solicitud.",
): Promise<T> {
  const url = `${getBaseUrl()}${path}`;
  const response = await fetch(url, {
    credentials: "include",
    ...options,
  });

  if (!response.ok) {
    const body = (await response.json()) as ApiErrorBody;
    throw new Error(normalizeErrorMessage(body.detail, fallbackError));
  }

  return (await response.json()) as T;
}

async function requestMaybe<T>(
  path: string,
  options: RequestInit = {},
): Promise<T | null> {
  const url = `${getBaseUrl()}${path}`;
  const response = await fetch(url, {
    credentials: "include",
    ...options,
  });

  if (response.status === 401) {
    return null;
  }

  if (!response.ok) {
    const body = (await response.json()) as ApiErrorBody;
    throw new Error(
      normalizeErrorMessage(body.detail, "Error en la solicitud."),
    );
  }

  return (await response.json()) as T;
}

async function requestVoid(
  path: string,
  options: RequestInit = {},
  fallbackError: string = "Error en la solicitud.",
): Promise<void> {
  const url = `${getBaseUrl()}${path}`;
  const response = await fetch(url, {
    credentials: "include",
    ...options,
  });

  if (!response.ok) {
    const body = (await response.json()) as ApiErrorBody;
    throw new Error(normalizeErrorMessage(body.detail, fallbackError));
  }
}

async function requestWithFormData<T>(
  path: string,
  formData: FormData,
  fallbackError: string = "Error en la solicitud.",
): Promise<T> {
  const url = `${getBaseUrl()}${path}`;
  const response = await fetch(url, {
    method: "POST",
    credentials: "include",
    body: formData,
  });

  if (!response.ok) {
    const body = (await response.json()) as ApiErrorBody;
    throw new Error(normalizeErrorMessage(body.detail, fallbackError));
  }

  return (await response.json()) as T;
}

export const api = {
  get: <T>(path: string, fallback?: string) =>
    request<T>(path, {}, fallback),

  getMaybe: <T>(path: string) =>
    requestMaybe<T>(path),

  post: <T>(path: string, body?: unknown, fallback?: string) =>
    request<T>(path, {
      method: "POST",
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    }, fallback),

  postVoid: (path: string, body?: unknown, fallback?: string) =>
    requestVoid(path, {
      method: "POST",
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    }, fallback),

  put: <T>(path: string, body: unknown, fallback?: string) =>
    request<T>(path, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }, fallback),

  deleteVoid: (path: string, fallback?: string) =>
    requestVoid(path, {
      method: "DELETE",
    }, fallback),

  postFormData: <T>(path: string, formData: FormData, fallback?: string) =>
    requestWithFormData<T>(path, formData, fallback),
};
