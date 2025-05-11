import { useState } from "react";
import SearchForm, { type SearchParams } from "../components/SearchForm";

/** Minimal summary returned by /api/search */
interface BusinessSummary {
  slug: string;
  name: string;
  jurisdiction: string;
  status: number | string;
}

/** Full entity record returned by /api/entities/{slug} */
interface CorporateEntity {
  slug: string;
  name: string;
  jurisdiction: string;
  formed: string;
  officers: string[];
  status: string;
  notes?: string | null;
}

const API_BASE = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8001";

/**
 * Search page – allows users to query the back‑end, view matching
 * entities on the left, and inspect details on the right.
 */
export default function Search() {
  const [results, setResults] = useState<BusinessSummary[]>([]);
  const [selected, setSelected] = useState<CorporateEntity | null>(null);
  const [loading, setLoading] = useState(false);

  async function runSearch(params: SearchParams) {
    const stateCode = params.state?.trim().toLowerCase() ?? "";
    setLoading(true);
    setSelected(null);

    try {
      const url = stateCode
        ? `${API_BASE}/sos/${stateCode}?name=${encodeURIComponent(params.q)}`
        : `${API_BASE}/search?q=${encodeURIComponent(params.q)}`;

      const res = await fetch(url);
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);

      const json = await res.json();

      if (Array.isArray(json)) {
        setResults(json as BusinessSummary[]);
      } else if (json && typeof json === "object" && "slug" in json) {
        // API returned a single CorporateEntity – wrap it so the UI can display it
        const single = json as unknown as CorporateEntity;
        setResults([
          {
            slug: single.slug,
            name: single.name,
            jurisdiction: single.jurisdiction,
            status: single.status,
          },
        ]);
      } else {
        setResults([]);
        alert("No matching entities found.");
      }
    } catch (err) {
      console.error(err);
      alert("Search failed – see console for details.");
    } finally {
      setLoading(false);
    }
  }

  async function fetchDetails(slug: string) {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/entities/${slug}`);
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      setSelected(await res.json());
    } catch (err) {
      console.error(err);
      alert("Could not load entity details.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6 py-8">
      {/* Search bar */}
      <div className="rounded bg-white p-6 shadow">
        <SearchForm onSearch={runSearch} />
      </div>

      {/* Results + details grid */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* left column – search results */}
        <div className="rounded bg-white p-4 shadow">
          <h2 className="mb-3 text-lg font-semibold">Results</h2>
          {loading && results.length === 0 && (
            <p className="text-sm text-gray-400">Searching…</p>
          )}
          {results.length === 0 && !loading && (
            <p className="text-sm text-gray-400">No results yet</p>
          )}
          <ul className="space-y-2">
            {results.map((r) => {
              const statusDisplay =
                typeof r.status === "number"
                  ? ["PENDING", "ACTIVE", "IN_COMPLIANCE", "DELINQUENT", "DISSOLVED"][r.status] ?? r.status
                  : r.status;

              return (
                <li
                  key={r.slug}
                  className={`cursor-pointer rounded border p-2 ${
                    selected?.slug === r.slug
                      ? "border-indigo-500 bg-indigo-50"
                      : "border-gray-200 hover:bg-gray-50"
                  }`}
                  onClick={() => fetchDetails(r.slug)}
                >
                  <p className="font-medium">{r.name}</p>
                  <p className="text-xs text-gray-500">
                    {r.jurisdiction} · {statusDisplay}
                  </p>
                </li>
              );
            })}
          </ul>
        </div>

        {/* right column – details */}
        <div className="rounded bg-white p-4 shadow">
          {selected ? (
            <>
              <h2 className="mb-3 text-lg font-semibold">{selected.name}</h2>
              <dl className="grid grid-cols-3 gap-y-2 text-sm">
                <dt className="font-medium">Jurisdiction</dt>
                <dd className="col-span-2">{selected.jurisdiction}</dd>

                <dt className="font-medium">Formed</dt>
                <dd className="col-span-2">{selected.formed}</dd>

                <dt className="font-medium">Status</dt>
                <dd className="col-span-2">{selected.status}</dd>

                <dt className="font-medium">Officers</dt>
                <dd className="col-span-2">
                  {selected.officers.length
                    ? selected.officers.join(", ")
                    : "—"}
                </dd>

                {selected.notes && (
                  <>
                    <dt className="font-medium">Notes</dt>
                    <dd className="col-span-2 whitespace-pre-wrap">
                      {selected.notes}
                    </dd>
                  </>
                )}
              </dl>
            </>
          ) : (
            <p className="text-sm text-gray-400">
              Select an entity to view details
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
