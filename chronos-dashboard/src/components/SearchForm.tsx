import React, { useState, FormEvent } from "react";
import styles from './SearchForm.module.css';

/** Search provider options */
export type SearchProvider = 'cobalt' | 'edgar' | 'sos';

/** Params sent to the backend search endpoint */
export interface SearchParams {
  /** Free-text business name (required) */
  q: string;
  /** Two-letter state code; empty string === "all states" */
  state?: string;
  /** Search provider (Cobalt, EDGAR, or SoS) */
  provider?: SearchProvider;
  /** Whether to use Cobalt Intelligence API */
  use_cobalt?: boolean;
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

/** Complete list of US states and territories */
const STATES = [
  { code: "", label: "All States" },
  { code: "AL", label: "Alabama" },
  { code: "AK", label: "Alaska" },
  { code: "AZ", label: "Arizona" },
  { code: "AR", label: "Arkansas" },
  { code: "CA", label: "California" },
  { code: "CO", label: "Colorado" },
  { code: "CT", label: "Connecticut" },
  { code: "DE", label: "Delaware" },
  { code: "DC", label: "District of Columbia" },
  { code: "FL", label: "Florida" },
  { code: "GA", label: "Georgia" },
  { code: "HI", label: "Hawaii" },
  { code: "ID", label: "Idaho" },
  { code: "IL", label: "Illinois" },
  { code: "IN", label: "Indiana" },
  { code: "IA", label: "Iowa" },
  { code: "KS", label: "Kansas" },
  { code: "KY", label: "Kentucky" },
  { code: "LA", label: "Louisiana" },
  { code: "ME", label: "Maine" },
  { code: "MD", label: "Maryland" },
  { code: "MA", label: "Massachusetts" },
  { code: "MI", label: "Michigan" },
  { code: "MN", label: "Minnesota" },
  { code: "MS", label: "Mississippi" },
  { code: "MO", label: "Missouri" },
  { code: "MT", label: "Montana" },
  { code: "NE", label: "Nebraska" },
  { code: "NV", label: "Nevada" },
  { code: "NH", label: "New Hampshire" },
  { code: "NJ", label: "New Jersey" },
  { code: "NM", label: "New Mexico" },
  { code: "NY", label: "New York" },
  { code: "NC", label: "North Carolina" },
  { code: "ND", label: "North Dakota" },
  { code: "OH", label: "Ohio" },
  { code: "OK", label: "Oklahoma" },
  { code: "OR", label: "Oregon" },
  { code: "PA", label: "Pennsylvania" },
  { code: "RI", label: "Rhode Island" },
  { code: "SC", label: "South Carolina" },
  { code: "SD", label: "South Dakota" },
  { code: "TN", label: "Tennessee" },
  { code: "TX", label: "Texas" },
  { code: "UT", label: "Utah" },
  { code: "VT", label: "Vermont" },
  { code: "VA", label: "Virginia" },
  { code: "WA", label: "Washington" },
  { code: "WV", label: "West Virginia" },
  { code: "WI", label: "Wisconsin" },
  { code: "WY", label: "Wyoming" },
];

/**
 * Stand-alone search widget used on the Dashboard.
 * Keeps its own local form state and emits the query via `props.onSearch`.
 */
export const SearchForm: React.FC<SearchFormProps> = ({ 
  onSearch, 
  title = "Corporate Entity Search",
  description = "Search for business entities across multiple states and jurisdictions.",
  initialProvider = 'cobalt'
}) => {
  const [q, setQ] = useState("");
  const [state, setState] = useState("");
  const [provider, setProvider] = useState<SearchProvider>(initialProvider);

  /** Submit handler ⇒ bubble query up */
  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!q.trim()) return; // ignore empty queries
    
    // Send search params including the use_cobalt flag for backward compatibility
    onSearch({ 
      q: q.trim(), 
      state: state || undefined,
      provider,
      use_cobalt: provider === 'cobalt' // Set use_cobalt flag for compatibility
    });
  };

  return (
    <div className={styles.searchForm}>
      {title && <h2 className={styles.formHeader}>{title}</h2>}
      {description && <p className={styles.formDescription}>{description}</p>}
      
      <form onSubmit={handleSubmit}>
        {/* Search provider selection */}
        <div className={styles.radioGroup}>
          <label className={`${styles.radioLabel} ${provider === 'cobalt' ? 'bg-indigo-50 border border-indigo-100' : ''}`}>
            <input
              type="radio"
              name="searchProvider"
              className={styles.radioInput}
              checked={provider === 'cobalt'}
              onChange={() => setProvider('cobalt')}
            />
            <span className={styles.radioText}>Cobalt Intelligence</span>
          </label>
          <label className={`${styles.radioLabel} ${provider === 'edgar' ? 'bg-indigo-50 border border-indigo-100' : ''}`}>
            <input
              type="radio"
              name="searchProvider"
              className={styles.radioInput}
              checked={provider === 'edgar'}
              onChange={() => setProvider('edgar')}
            />
            <span className={styles.radioText}>SEC EDGAR</span>
          </label>
          <label className={`${styles.radioLabel} ${provider === 'sos' ? 'bg-indigo-50 border border-indigo-100' : ''}`}>
            <input
              type="radio"
              name="searchProvider"
              className={styles.radioInput}
              checked={provider === 'sos'}
              onChange={() => setProvider('sos')}
            />
            <span className={styles.radioText}>Secretary of State</span>
          </label>
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
              placeholder={provider === 'edgar' ? "Apple Inc. or AAPL" : "University Health Foundation"}
              className={styles.formControl}
              autoFocus
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