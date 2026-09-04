/**
 * Centralised API base URL and shared fetch helper.
 * All API modules import from here.
 */
const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const WS_URL   = import.meta.env.VITE_WS_URL  ?? "ws://localhost:8000";

export { BASE_URL, WS_URL };

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`API ${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}
