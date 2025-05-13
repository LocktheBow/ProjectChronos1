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
  // build init object so we add the JSON header only when it’s needed
  const init: RequestInit = { ...opts };

  // add the Content‑Type header only for requests that *send* a body
  if ((init.method ?? "GET").toUpperCase() !== "GET") {
    init.headers = {
      "Content-Type": "application/json",
      ...(init.headers ?? {}),
    };
  }

  const res = await fetch(`${API_BASE}${path}`, init);

  if (!res.ok) {
    // surface backend error text – useful for debugging
    throw new Error(await res.text());
  }
  return res.json() as Promise<T>;
}

/* -------------------------------------------------------------------------- */
/* Typed helpers for the two backend routes we currently use                 */
/* -------------------------------------------------------------------------- */

/** Counts returned by GET /status */
interface StatusCounts {
  ACTIVE: number;
  PENDING: number;
  IN_COMPLIANCE: number;
  DELINQUENT: number;
  DISSOLVED: number;
}

/** Simple fetch for the /status endpoint */
export async function fetchStatus(
  signal?: AbortSignal,
): Promise<StatusCounts> {
  const raw = await api<Partial<StatusCounts>>("/status", { signal });
  // normalise → ensure every bucket exists, defaulting to 0
  return {
    ACTIVE: raw.ACTIVE ?? 0,
    PENDING: raw.PENDING ?? 0,
    IN_COMPLIANCE: raw.IN_COMPLIANCE ?? 0,
    DELINQUENT: raw.DELINQUENT ?? 0,
    DISSOLVED: raw.DISSOLVED ?? 0,
  };
}

/* -------------------------------------------------------------------------- */
/* Relationship Graph                                                         */
/* -------------------------------------------------------------------------- */

// Interfaces are now defined locally in each component to avoid import issues
interface GraphNode {
  id: string;
  name: string;
  status: string;
  jurisdiction: string;
  type: 'PRIMARY' | 'SUBSIDIARY';
}

interface GraphLink {
  source: string;
  target: string;
  value: number; // Ownership percentage
}

interface RelationshipGraph {
  nodes: GraphNode[];
  links: GraphLink[];
}

/**
 * Fetch the relationship graph from the /relationships endpoint
 */
export async function fetchRelationships(
  signal?: AbortSignal,
): Promise<RelationshipGraph> {
  return api<RelationshipGraph>("/relationships", { signal });
}

/**
 * Fetch shell company detection results
 */
interface ShellCompany {
  slug: string;
  name: string;
  risk_score: number;
}

export async function fetchShellDetection(
  signal?: AbortSignal,
): Promise<ShellCompany[]> {
  return api<ShellCompany[]>("/shell-detection", { signal });
}

/* -------------------------------------------------------------------------- */
/* Business search                                                            */
/* -------------------------------------------------------------------------- */

interface EntityHit {
  slug: string;
  name: string;
  jurisdiction: string;
  status: string;
  formed: string;            // ISO date string
}

/**
 * Query the /search endpoint (GET) and return an array of entity hits.
 *
 * @param q     Full‑text business name query (required)
 * @param state Optional 2‑letter state filter
 */
export function searchEntities(
  q: string,
  state?: string,
  signal?: AbortSignal,
): Promise<EntityHit[]> {
  const params = new URLSearchParams({ q });
  if (state) params.append("state", state);
  return api<EntityHit[]>(`/search?${params.toString()}`, { signal });
}

/* -------------------------------------------------------------------------- */
/* React helper ‑ live /status polling                                       */
/* -------------------------------------------------------------------------- */
import { useEffect, useState } from "react";

/**
 * Small React convenience hook that polls the `/status` endpoint every
 * `pollMs` milliseconds (15 s by default) and returns a tuple:
 *
 *   { data, error, isLoading }
 *
 * ...where `data` is {@link StatusCounts} once loaded (five lifecycle buckets).
 */
export function useStatus(pollMs: number = 15_000) {
  const [data, setData] = useState<StatusCounts | undefined>();
  const [error, setError] = useState<unknown>();
  const isLoading = !data && !error;

  useEffect(() => {
    const controller = new AbortController();

    async function tick() {
      try {
        const json = await fetchStatus(controller.signal);
        setData(json);
        setError(undefined);
      } catch (err) {
        if ((err as DOMException)?.name !== "AbortError") {
          setError(err);
        }
      }
    }

    tick();                         // initial fetch
    const id = setInterval(tick, pollMs);

    return () => {
      controller.abort();
      clearInterval(id);
    };
  }, [pollMs]);

  return { data, error, isLoading };
}