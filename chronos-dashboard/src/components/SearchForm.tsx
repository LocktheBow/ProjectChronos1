import React, { useState, FormEvent } from "react";
import styles from './SearchForm.module.css';

/** Search provider options */
export type SearchProvider = 'dataaxle' | 'edgar' | 'sos';

/** Params sent to the backend search endpoint */
export interface SearchParams {
  /** Free-text business name (required) */
  q: string;
  /** Two-letter state code; empty string === "all states" */
  state?: string;
  /** Search provider (Data Axle, EDGAR, or SoS) */
  provider?: SearchProvider;
}

interface SearchFormProps {
  /** Called when the user clicks *Search* or presses ⏎ */
  onSearch: (params: SearchParams) => void;
  /** Optional title for the search form */
  title?: string;
  /** Optional description for the search form */
  description?: string;
  /** Optional initial search provider */
  initialProvider?: SearchProvider;
}

/** Minimal list for now – extend when other scrapers are added */
const STATES = [
  { code: "", label: "All States" },
  { code: "DE", label: "Delaware" },
  { code: "CA", label: "California" },
  { code: "NY", label: "New York" },
  { code: "TX", label: "Texas" },
  { code: "FL", label: "Florida" },
  { code: "IL", label: "Illinois" },
  { code: "WA", label: "Washington" },
  { code: "MA", label: "Massachusetts" },
];

/**
 * Stand-alone search widget used on the Dashboard (and later on a
 * global header).  Keeps its own local form state and emits the query
 * via `props.onSearch`.
 */
export const SearchForm: React.FC<SearchFormProps> = ({ 
  onSearch, 
  title = "Corporate Entity Search",
  description = "Search for business entities across multiple states and jurisdictions.",
  initialProvider = 'dataaxle'
}) => {
  const [q, setQ] = useState("");
  const [state, setState] = useState("");
  const [provider, setProvider] = useState<SearchProvider>(initialProvider);

  /** Submit handler ⇒ bubble query up */
  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!q.trim()) return; // ignore empty queries
    onSearch({ 
      q: q.trim(), 
      state: state || undefined,
      provider 
    });
  };

  return (
    <div className={styles.searchForm}>
      {title && <h2 className={styles.formHeader}>{title}</h2>}
      {description && <p className={styles.formDescription}>{description}</p>}
      
      <form onSubmit={handleSubmit}>
        {/* Search provider selection */}
        <div className="mb-4">
          <div className="flex flex-col sm:flex-row gap-3">
            <label className="inline-flex items-center">
              <input
                type="radio"
                className="form-radio h-4 w-4 text-indigo-600"
                checked={provider === 'dataaxle'}
                onChange={() => setProvider('dataaxle')}
              />
              <span className="ml-2 text-sm">Data Axle</span>
            </label>
            <label className="inline-flex items-center">
              <input
                type="radio"
                className="form-radio h-4 w-4 text-indigo-600"
                checked={provider === 'edgar'}
                onChange={() => setProvider('edgar')}
              />
              <span className="ml-2 text-sm">SEC EDGAR</span>
            </label>
            <label className="inline-flex items-center">
              <input
                type="radio"
                className="form-radio h-4 w-4 text-indigo-600"
                checked={provider === 'sos'}
                onChange={() => setProvider('sos')}
              />
              <span className="ml-2 text-sm">Secretary of State</span>
            </label>
          </div>
        </div>
        
        <div className={styles.inputGroup}>
          {/* business name input */}
          <div className={styles.formGroup}>
            <label className={styles.formLabel}>
              {provider === 'edgar' ? 'Company Name or Ticker' : 'Business Name'}
            </label>
            <input
              type="text"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder={provider === 'edgar' ? "Apple Inc. or AAPL" : "ACME LLC"}
              className={styles.formControl}
            />
          </div>

          {/* state dropdown - hide for EDGAR search */}
          {provider !== 'edgar' && (
            <div className={styles.formGroup}>
              <label className={styles.formLabel}>
                State (Optional)
              </label>
              <select
                value={state}
                onChange={(e) => setState(e.target.value)}
                className={styles.select}
              >
                {STATES.map((s) => (
                  <option key={s.code} value={s.code}>
                    {s.label}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {/* submit */}
        <div className={styles.formActions}>
          <button type="submit" className={styles.btnPrimary}>
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
            Search
          </button>
        </div>
      </form>
    </div>
  );
};

export default SearchForm;        // default export for convenience
export type { SearchParams, SearchProvider };  // re-export the *types* for consumers