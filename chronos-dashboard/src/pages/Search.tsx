import { useState, Fragment, useEffect } from "react";
import SearchForm, { type SearchParams, type SearchProvider } from "../components/SearchForm";
import StatusChart from "../components/StatusChart";
import { 
  searchEntities, 
  searchSos, 
  searchAxle, 
  searchEdgar, 
  getCachedSearchResults 
} from "../hooks/useApi";

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
  const [offlineMode, setOfflineMode] = useState(false);
  const [lastSearchParams, setLastSearchParams] = useState<SearchParams | null>(null);

  // Function to check API availability
  const checkApiAvailability = async () => {
    try {
      const res = await fetch(`${API_BASE}/`);
      setOfflineMode(!res.ok);
      return res.ok;
    } catch (error) {
      console.log("API appears to be offline:", error);
      setOfflineMode(true);
      return false;
    }
  };

  // Check API availability on component mount
  useEffect(() => {
    checkApiAvailability();
  }, []);

  async function runSearch(params: SearchParams) {
    const stateCode = params.state?.trim().toLowerCase() ?? "";
    const provider = params.provider || 'dataaxle';
    
    setLoading(true);
    setSelected(null);
    setLastSearchParams(params);

    try {
      // Check if API is available
      const isApiAvailable = await checkApiAvailability();
      let searchResults: BusinessSummary[] = [];

      if (isApiAvailable) {
        // API is available, try to fetch fresh results
        try {
          if (provider === 'edgar') {
            // Use SEC EDGAR search
            const edgarResults = await searchEdgar(params.q);
            searchResults = edgarResults.map(company => ({
              slug: (company.name || company.filing_id || '').toLowerCase().replace(/[^a-z0-9]/g, '-'),
              name: company.name || `Filing ${company.form}`,
              jurisdiction: company.incorporation || 'US',
              status: 'ACTIVE', // SEC doesn't provide status information
              // Include filing information if available
              ...(company.filing_date ? { formed: company.filing_date } : {})
            }));
          } else if (provider === 'dataaxle') {
            // Use Data Axle search
            searchResults = await searchAxle(params.q, stateCode);
          } else if (provider === 'sos') {
            // Use Secretary of State search
            if (stateCode) {
              // If state is specified, use the sosearch endpoint
              searchResults = await searchSos(params.q, stateCode);
            } else {
              // Otherwise use the regular search endpoint
              searchResults = await searchEntities(params.q, undefined);
            }
          }
          setResults(searchResults);
          setOfflineMode(false);
        } catch (err) {
          console.error("Error fetching from API:", err);
          // Fall back to cached results if API request fails
          const cachedResults = getCachedSearchResults(params.q, stateCode);
          if (cachedResults && cachedResults.length > 0) {
            searchResults = cachedResults;
            setResults(searchResults);
            setOfflineMode(true);
          } else {
            setResults([]);
            alert("Search failed and no cached results found.");
          }
        }
      } else {
        // API is not available, use cached results
        const cachedResults = getCachedSearchResults(params.q, stateCode);
        if (cachedResults && cachedResults.length > 0) {
          searchResults = cachedResults;
          setResults(searchResults);
        } else {
          setResults([]);
          alert("API is offline and no cached results found for this search.");
        }
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
      // First check if we're in offline mode
      if (offlineMode) {
        // In offline mode, just show basic information from the results
        const matchingEntity = results.find(r => r.slug === slug);
        if (matchingEntity) {
          // Create a simplified entity with available data
          setSelected({
            slug: matchingEntity.slug,
            name: matchingEntity.name,
            jurisdiction: matchingEntity.jurisdiction,
            formed: "Not available in offline mode",
            officers: [],
            status: typeof matchingEntity.status === 'string' ? 
              matchingEntity.status : 
              ["PENDING", "ACTIVE", "IN_COMPLIANCE", "DELINQUENT", "DISSOLVED"][matchingEntity.status as number] || "Unknown"
          });
          return;
        }
      }
      
      // If we're online, fetch from API
      const res = await fetch(`${API_BASE}/entities/${slug}`);
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      setSelected(await res.json());
    } catch (err) {
      console.error(err);
      // If API fetch fails, check if the entity is in our results and use that
      const matchingEntity = results.find(r => r.slug === slug);
      if (matchingEntity) {
        setSelected({
          slug: matchingEntity.slug,
          name: matchingEntity.name,
          jurisdiction: matchingEntity.jurisdiction,
          formed: "Not available offline",
          officers: [],
          status: typeof matchingEntity.status === 'string' ? 
            matchingEntity.status : 
            ["PENDING", "ACTIVE", "IN_COMPLIANCE", "DELINQUENT", "DISSOLVED"][matchingEntity.status as number] || "Unknown"
        });
      } else {
        alert("Could not load entity details.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-8 py-8 pb-20">
      {/* Search bar */}
      <div className="rounded bg-white p-6 shadow">
        <SearchForm onSearch={runSearch} />
        {offlineMode && (
          <div className="mt-2 rounded-md bg-amber-50 px-3 py-2 border border-amber-200">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-amber-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                  <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v4.5a.75.75 0 01-1.5 0v-4.5A.75.75 0 0110 5zm0 10a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-amber-800">Offline Mode</h3>
                <div className="mt-1 text-sm text-amber-700">
                  <p>Connection to the API is unavailable. Showing cached results.</p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Results + details grid */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* left column – search results */}
        <div className="rounded bg-white p-4 shadow max-h-[65vh] overflow-y-auto scrollbar-thin scrollbar-thumb-gray-300">
          <div className="flex justify-between items-center mb-3">
            <h2 className="text-lg font-semibold">Results</h2>
            {offlineMode && results.length > 0 && (
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800">
                <svg className="-ml-0.5 mr-1.5 h-2 w-2 text-amber-400" fill="currentColor" viewBox="0 0 8 8">
                  <circle cx="4" cy="4" r="3" />
                </svg>
                Cached
              </span>
            )}
          </div>
          {loading && results.length === 0 && (
            <Fragment>
              {[...Array(4)].map((_,i)=>(
                <div key={i} className="h-12 rounded border border-gray-200 bg-gray-100 animate-pulse" />
              ))}
            </Fragment>
          )}
          {results.length === 0 && !loading && (
            <p className="text-sm text-gray-400">No results yet</p>
          )}
          <ul className="space-y-2 divide-y divide-gray-100" aria-live="polite">
            {results.map((r) => {
              const statusDisplay =
                typeof r.status === "number"
                  ? ["PENDING", "ACTIVE", "IN_COMPLIANCE", "DELINQUENT", "DISSOLVED"][r.status] ?? r.status
                  : r.status;

              return (
                <li
                  key={r.slug}
                  className={`cursor-pointer rounded border p-2 transition-colors duration-150 ${
                    selected?.slug === r.slug
                      ? "border-indigo-500 bg-indigo-50 ring-2 ring-indigo-400"
                      : "border-gray-200 hover:bg-[#F9FAFB]"
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
        <div className="rounded bg-white p-4 shadow max-h-[65vh] overflow-y-auto scrollbar-thin scrollbar-thumb-gray-300">
          {selected ? (
            <>
              <div className="flex justify-between items-center mb-3">
                <h2 className="text-lg font-semibold">{selected.name}</h2>
                {offlineMode && (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800">
                    <svg className="-ml-0.5 mr-1.5 h-2 w-2 text-amber-400" fill="currentColor" viewBox="0 0 8 8">
                      <circle cx="4" cy="4" r="3" />
                    </svg>
                    Limited Data (Offline)
                  </span>
                )}
              </div>
              <dl className="grid grid-cols-3 gap-y-2 text-sm">
                <dt className="font-medium">Jurisdiction</dt>
                <dd className="col-span-2">{selected.jurisdiction}</dd>

                <dt className="font-medium">Formed</dt>
                <dd className="col-span-2">
                  {selected.formed && selected.formed.includes("Not available") ? (
                    <span className="text-amber-600">{selected.formed}</span>
                  ) : (
                    selected.formed
                  )}
                </dd>

                <dt className="font-medium">Status</dt>
                <dd className="col-span-2">{selected.status}</dd>

                <dt className="font-medium">Officers</dt>
                <dd className="col-span-2">
                  {selected.officers.length
                    ? selected.officers.join(", ")
                    : offlineMode ? (
                        <span className="text-amber-600">Not available in offline mode</span>
                      ) : (
                        "—"
                      )}
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
              
              {offlineMode && (
                <div className="mt-4 rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-700 border border-amber-200">
                  <p className="font-medium">Limited data available in offline mode</p>
                  <p className="mt-1">Some entity details may be missing or incomplete while you're offline.</p>
                </div>
              )}
            </>
          ) : (
            loading ? (
              <div className="flex h-full items-center justify-center py-10">
                <svg className="h-8 w-8 animate-spin text-indigo-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
              </div>
            ) : (
              <p className="text-sm text-gray-400">
                Select an entity to view details
              </p>
            )
          )}
        </div>
      </div>

      {/* portfolio status snapshot */}
      <section className="rounded bg-white p-4 shadow overflow-x-auto">
        <h2 className="mb-3 text-lg font-semibold">Portfolio status</h2>
        <StatusChart />
      </section>
    </div>
  );
}
