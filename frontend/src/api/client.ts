import { getAccessToken, renewAccessToken } from "../auth";
import type { RecordInput, RRSet, ZoneCreateInput, ZoneDetail, ZoneSummary } from "./types";

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
    public code?: string,
  ) {
    super(detail);
  }
}

/** Picks the UI surface a caught error belongs on: form-adjacent, banner, or plain text. */
export function formatError(err: unknown): string {
  return err instanceof ApiError ? err.detail : String(err);
}

async function request<T>(path: string, init?: RequestInit, isRetry = false): Promise<T> {
  const token = await getAccessToken();
  const headers = new Headers(init?.headers);
  headers.set("Content-Type", "application/json");
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`/api${path}`, { ...init, headers });

  if (response.status === 401 && !isRetry) {
    const renewed = await renewAccessToken();
    if (renewed) {
      return request<T>(path, init, true);
    }
  }

  if (!response.ok) {
    let detail = response.statusText;
    let code: string | undefined;
    try {
      const body = await response.json();
      if (body.detail) {
        detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
      }
      if (typeof body.code === "string") {
        code = body.code;
      }
    } catch {
      // Non-JSON error body: keep the status text.
    }
    throw new ApiError(response.status, detail, code);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export function getZones(): Promise<ZoneSummary[]> {
  return request("/zones");
}

export function getZone(zoneId: string): Promise<ZoneDetail> {
  return request(`/zones/${encodeURIComponent(zoneId)}`);
}

export function createZone(input: ZoneCreateInput): Promise<ZoneSummary> {
  return request("/zones", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function deleteZone(zoneId: string): Promise<void> {
  return request(`/zones/${encodeURIComponent(zoneId)}`, {
    method: "DELETE",
  });
}

export function createRecord(zoneId: string, input: RecordInput): Promise<RRSet> {
  return request(`/zones/${encodeURIComponent(zoneId)}/records`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function updateRecord(zoneId: string, input: RecordInput): Promise<RRSet> {
  return request(`/zones/${encodeURIComponent(zoneId)}/records`, {
    method: "PUT",
    body: JSON.stringify(input),
  });
}

export function deleteRecord(zoneId: string, name: string, type: string): Promise<void> {
  const query = new URLSearchParams({ name, type });
  return request(`/zones/${encodeURIComponent(zoneId)}/records?${query}`, {
    method: "DELETE",
  });
}
