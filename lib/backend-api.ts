const DEFAULT_BACKEND_API_BASE = "http://127.0.0.1:8000";

export function getBackendApiBase(): string {
  return (process.env.BACKEND_API_BASE || DEFAULT_BACKEND_API_BASE).replace(/\/$/, "");
}

export function getInternalApiSecret(): string {
  return (process.env.INTERNAL_API_SECRET || "").trim();
}

export function backendHeaders(contentType = "application/json"): Headers {
  const headers = new Headers();
  if (contentType) headers.set("Content-Type", contentType);

  const internalSecret = getInternalApiSecret();
  if (internalSecret) {
    headers.set("x-internal-api-secret", internalSecret);
  }

  return headers;
}
