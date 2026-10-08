const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "").replace(/\/$/, "");

// Access token lives in memory only (never localStorage). Cleared on full reload,
// then restored via the HttpOnly refresh cookie (see auth-context).
let accessToken: string | null = null;
let refreshPromise: Promise<string | null> | null = null;

export function setAccessToken(t: string | null) {
  accessToken = t;
}
export function getAccessToken() {
  return accessToken;
}

type ErrorPayload = {
  detail?: unknown;
  errors?: unknown;
  title?: unknown;
};

function validationMessage(detail: unknown): string | null {
  if (!Array.isArray(detail)) return null;

  const messages = detail
    .map((issue) => {
      if (!issue || typeof issue !== "object") return null;
      const value = issue as { loc?: unknown; msg?: unknown };
      const field = Array.isArray(value.loc)
        ? value.loc.filter((part) => part !== "body").join(".")
        : "";
      const message = typeof value.msg === "string" ? value.msg : null;
      return message ? (field ? `${field}: ${message}` : message) : null;
    })
    .filter((message): message is string => Boolean(message));

  return messages.length ? messages.join(" ") : null;
}

export async function getApiErrorMessage(
  response: Response,
  fallback: string,
): Promise<string> {
  // Do not surface implementation details from unexpected server failures.
  if (response.status >= 500) return fallback;

  const payload = (await response.json().catch(() => ({}))) as ErrorPayload;
  const detailMessage = validationMessage(payload.detail);
  if (detailMessage) return detailMessage;
  if (typeof payload.detail === "string") return payload.detail;

  if (payload.errors && typeof payload.errors === "object") {
    const messages = Object.values(payload.errors as Record<string, unknown>)
      .flatMap((value) => (Array.isArray(value) ? value : [value]))
      .filter((value): value is string => typeof value === "string");
    if (messages.length) return messages.join(" ");
  }

  if (typeof payload.title === "string") return payload.title;
  return fallback;
}

// Single-flight: concurrent 401s share one refresh, so we never use a token
// that a parallel refresh has already rotated + revoked.
export async function refreshAccessToken(): Promise<string | null> {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const res = await fetch(`${API_BASE}/api/auth/refresh`, {
          method: "POST",
          credentials: "include",
        });
        if (!res.ok) return null;
        const data = (await res.json()) as { accessToken?: unknown };
        if (typeof data.accessToken !== "string") return null;
        accessToken = data.accessToken;
        return accessToken;
      } catch {
        return null;
      } finally {
        refreshPromise = null;
      }
    })();
  }
  return refreshPromise;
}

export async function apiFetch(
  path: string,
  options: RequestInit = {},
  retry = true,
): Promise<Response> {
  const headers = new Headers(options.headers);
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  if (options.body && !headers.has("Content-Type"))
    headers.set("Content-Type", "application/json");

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
    credentials: "include",
  });

  if (res.status === 401 && retry) {
    const newToken = await refreshAccessToken();
    if (newToken) return apiFetch(path, options, false);
  }
  return res;
}

export { API_BASE };
