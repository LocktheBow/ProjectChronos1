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
  //   vite env            explicit fallback →   explicit http scheme
  import.meta.env.VITE_API_BASE ?? `http://${window.location.hostname}:8001`;

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
 * @param signal Optional AbortSignal for cancellation
 * @param loadExamples Optional flag to force loading example relationships
 */
export async function fetchRelationships(
  signal?: AbortSignal,
  loadExamples?: boolean,
): Promise<RelationshipGraph> {
  const url = loadExamples 
    ? "/relationships?load_examples=true" 
    : "/relationships";
  return api<RelationshipGraph>(url, { signal });
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
interface CachedSearch {
  timestamp: number;
  query: string;
  state?: string;
  results: EntityHit[];
}

// Helper function to get cached search results
function getSearchCache(): Record<string, CachedSearch> {
  try {
    const cached = localStorage.getItem('chronos_search_cache');
    return cached ? JSON.parse(cached) : {};
  } catch (e) {
    console.error('Error reading search cache:', e);
    return {};
  }
}

// Helper function to save search results to cache
function saveSearchToCache(query: string, state: string | undefined, results: EntityHit[]): void {
  try {
    const cache = getSearchCache();
    const cacheKey = `${query}|${state || ''}`;
    
    // Update cache with new results
    cache[cacheKey] = {
      timestamp: Date.now(),
      query,
      state,
      results
    };
    
    // Prune old entries (keep last 20)
    const entries = Object.entries(cache);
    if (entries.length > 20) {
      const sortedEntries = entries.sort((a, b) => b[1].timestamp - a[1].timestamp);
      const pruned = Object.fromEntries(sortedEntries.slice(0, 20));
      localStorage.setItem('chronos_search_cache', JSON.stringify(pruned));
    } else {
      localStorage.setItem('chronos_search_cache', JSON.stringify(cache));
    }
  } catch (e) {
    console.error('Error saving to search cache:', e);
  }
}

/**
 * Search entities using the main search endpoint (which now uses Cobalt Intelligence)
 */
export function searchEntities(
  q: string,
  state?: string,
  signal?: AbortSignal,
  useCobalt: boolean = true
): Promise<EntityHit[]> {
  const params = new URLSearchParams({ q });
  if (state) params.append("state", state);
  if (useCobalt !== undefined) params.append("use_cobalt", String(useCobalt));
  
  return api<EntityHit[]>(`/search?${params.toString()}`, { signal })
    .then(results => {
      // Cache successful results
      saveSearchToCache(q, state, results);
      return results;
    });
}

/**
 * Search using state-specific Secretary of State scrapers
 */
export function searchSos(
  q: string,
  jurisdiction?: string,
  signal?: AbortSignal,
): Promise<EntityHit[]> {
  const params = new URLSearchParams({ q });
  if (jurisdiction) params.append("jurisdiction", jurisdiction);
  
  return api<EntityHit[]>(`/sosearch?${params.toString()}`, { signal })
    .then(results => {
      // Cache successful results
      saveSearchToCache(q, jurisdiction, results);
      return results;
    });
}

/**
 * Search using Cobalt Intelligence API
 */
export function searchCobalt(
  q: string,
  state?: string,
  signal?: AbortSignal,
): Promise<EntityHit[]> {
  const params = new URLSearchParams({ q });
  if (state) params.append("state", state);
  
  return api<EntityHit[]>(`/cobalt/search?${params.toString()}`, { signal })
    .then(results => {
      // Cache successful results
      saveSearchToCache(q, state, results);
      return results;
    });
}

/**
 * Search using SEC EDGAR API
 */
export function searchEdgar(
  q: string,
  limit: number = 10,
  signal?: AbortSignal,
): Promise<any[]> {
  const params = new URLSearchParams({ q });
  if (limit) params.append("limit", String(limit));
  
  return api<any[]>(`/edgar/search?${params.toString()}`, { signal });
}

/**
 * Get SEC filings for a company by CIK
 */
export function getEdgarFilings(
  cik: string,
  forms?: string[],
  limit: number = 10,
  signal?: AbortSignal,
): Promise<any[]> {
  const params = new URLSearchParams();
  if (forms && forms.length > 0) params.append("forms", forms.join(','));
  if (limit) params.append("limit", String(limit));
  
  return api<any[]>(`/edgar/filings/${cik}?${params.toString()}`, { signal });
}

/**
 * Get cached search results, if any exist
 * @param q The search query
 * @param state Optional state/jurisdiction filter
 * @returns Cached results or null if not found
 */
export function getCachedSearchResults(q: string, state?: string): EntityHit[] | null {
  try {
    const cache = getSearchCache();
    const cacheKey = `${q}|${state || ''}`;
    const cached = cache[cacheKey];
    
    if (cached) {
      // Check if cache is still valid (24 hours)
      const now = Date.now();
      const cacheAge = now - cached.timestamp;
      const CACHE_TTL = 24 * 60 * 60 * 1000; // 24 hours
      
      if (cacheAge < CACHE_TTL) {
        return cached.results;
      }
    }
    
    return null;
  } catch (e) {
    console.error('Error retrieving cached search results:', e);
    return null;
  }
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