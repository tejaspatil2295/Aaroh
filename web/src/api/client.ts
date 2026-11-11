import { Capacitor } from "@capacitor/core";
import { SecureStorage } from "@aparajita/capacitor-secure-storage";

export const isNative = Capacitor.isNativePlatform();
const SERVER_KEY = "aaroh.server";
const REFRESH_KEY = "aaroh.refresh";

/** Backend base URL. Web uses same-origin `/api`; the Android app talks to a configurable server. */
export function getServer(): string {
  if (!isNative) return import.meta.env.VITE_API_URL || "";
  return localStorage.getItem(SERVER_KEY) || import.meta.env.VITE_API_URL || "";
}
export function setServer(url: string) {
  localStorage.setItem(SERVER_KEY, url.replace(/\/+$/, ""));
}

let accessToken: string | null = null;
let refreshing: Promise<boolean> | null = null;
let onLogout: (() => void) | null = null;
export const setLogoutHandler = (fn: () => void) => (onLogout = fn);

// Refresh tokens: Android Keystore-backed secure storage on device; httpOnly cookie on the web.
async function storeRefresh(token: string | null) {
  if (!isNative) return;
  if (token) await SecureStorage.set(REFRESH_KEY, token);
  else await SecureStorage.remove(REFRESH_KEY).catch(() => undefined);
}
async function readRefresh(): Promise<string | null> {
  if (!isNative) return null;
  try {
    return ((await SecureStorage.get(REFRESH_KEY)) as string | null) ?? null;
  } catch {
    return null;
  }
}

export class ApiError extends Error {
  constructor(public status: number, message: string, public body?: unknown) {
    super(message);
  }
}

type Tokens = { access_token: string; refresh_token: string };

export async function setSession(t: Tokens) {
  accessToken = t.access_token;
  await storeRefresh(t.refresh_token);
}

export async function refreshSession(): Promise<boolean> {
  if (!refreshing) {
    refreshing = (async () => {
      const rt = await readRefresh();
      if (isNative && !rt) return false;
      try {
        const r = await fetch(`${getServer()}/api/v1/auth/refresh`, {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(rt ? { refresh_token: rt } : {}),
        });
        if (!r.ok) return false;
        await setSession(await r.json());
        return true;
      } catch {
        return false;
      }
    })().finally(() => setTimeout(() => (refreshing = null), 0));
  }
  return refreshing;
}

export async function clearSession() {
  const rt = await readRefresh();
  try {
    await fetch(`${getServer()}/api/v1/auth/logout`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(rt ? { refresh_token: rt } : {}),
    });
  } catch {
    /* offline logout still clears local state */
  }
  accessToken = null;
  await storeRefresh(null);
}

function errorMessage(body: any, status: number): string {
  if (body?.detail) {
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail))
      return body.detail.map((d: any) => `${(d.loc || []).slice(1).join(".")}: ${d.msg}`).join("; ");
  }
  return `Request failed (${status})`;
}

export async function api<T = any>(path: string, opts: RequestInit & { json?: unknown; raw?: boolean } = {}, retry = true): Promise<T> {
  const headers = new Headers(opts.headers);
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  let body = opts.body;
  if (opts.json !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(opts.json);
  }
  let res: Response;
  try {
    res = await fetch(`${getServer()}/api/v1${path}`, { ...opts, headers, body, credentials: "include" });
  } catch {
    throw new ApiError(0, "Can't reach the AAROH server. Check your connection or server address.");
  }
  if (res.status === 401 && retry && !path.startsWith("/auth/")) {
    if (await refreshSession()) return api<T>(path, opts, false);
    onLogout?.();
  }
  if (!res.ok) {
    const b = await res.json().catch(() => null);
    throw new ApiError(res.status, errorMessage(b, res.status), b);
  }
  if (opts.raw) return res as unknown as T;
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const get = <T = any>(p: string) => api<T>(p);
export const post = <T = any>(p: string, json?: unknown) => api<T>(p, { method: "POST", json: json ?? {} });
export const patch = <T = any>(p: string, json: unknown) => api<T>(p, { method: "PATCH", json });
export const put = <T = any>(p: string, json: unknown) => api<T>(p, { method: "PUT", json });
export const del = (p: string, json?: unknown) => api(p, { method: "DELETE", json });

export function qs(params: Record<string, string | number | boolean | undefined | null>) {
  const s = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => v !== undefined && v !== null && v !== "" && s.set(k, String(v)));
  const out = s.toString();
  return out ? `?${out}` : "";
}
