/**
 * Small wrapper around fetch that automatically points to the FastAPI backend.
 *
 * By default we assume the backend runs on the same machine on port 8001.
 * If you need a different host/port (e.g. in production or a dev‑container)
 * set `VITE_API_BASE` in your .env file, e.g.
 *
 *   VITE_API_BASE="https://chronos.example.com"
 */
const API_BASE =
  //   vite env            explicit fallback →   scheme//host:8001
  import.meta.env.VITE_API_BASE ?? `//${window.location.hostname}:8001`;

export async function api<T>(
  path: string,
  opts: RequestInit = {},
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });

  if (!res.ok) {
    // surface backend error text – useful for debugging
    throw new Error(await res.text());
  }
  return res.json() as Promise<T>;
}