import React, { useState, FormEvent } from "react";

/** Params sent to the backend search endpoint (`/sos/{state}`) */
export interface SearchParams {
  /** Free-text business name (required) */
  q: string;
  /** Two-letter state code; empty string === “all states” */
  state?: string;
}

interface SearchFormProps {
  /** Called when the user clicks *Search* or presses ⏎ */
  onSearch: (params: SearchParams) => void;
}

/** Minimal list for now – extend when other scrapers are added */
const STATES = [
  { code: "", label: "All States" },
  { code: "DE", label: "Delaware" },
  { code: "CA", label: "California" },
  { code: "NY", label: "New York" },
  { code: "TX", label: "Texas" },
];

/**
 * Stand-alone search widget used on the Dashboard (and later on a
 * global header).  Keeps its own local form state and emits the query
 * via `props.onSearch`.
 */
export const SearchForm: React.FC<SearchFormProps> = ({ onSearch }) => {
  const [q, setQ] = useState("");
  const [state, setState] = useState("");

  /** Submit handler ⇒ bubble query up */
  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!q.trim()) return; // ignore empty queries
    onSearch({ q: q.trim(), state: state || undefined });
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-col gap-2 md:flex-row md:items-end"
    >
      {/* business name input */}
      <div className="flex-1">
        <label className="block text-sm font-medium text-gray-700">
          Business Name
        </label>
        <input
          type="text"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="ACME LLC"
          className="mt-1 w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
        />
      </div>

      {/* state dropdown */}
      <div className="md:w-48">
        <label className="block text-sm font-medium text-gray-700">
          State (Optional)
        </label>
        <select
          value={state}
          onChange={(e) => setState(e.target.value)}
          className="mt-1 w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
        >
          {STATES.map((s) => (
            <option key={s.code} value={s.code}>
              {s.label}
            </option>
          ))}
        </select>
      </div>

      {/* submit */}
      <button
        type="submit"
        className="mt-4 rounded-md bg-indigo-600 px-4 py-2 font-semibold text-white shadow-sm hover:bg-indigo-700 md:mt-0"
      >
        Search
      </button>
    </form>
  );
};

export default SearchForm;        // default export for convenience
export type { SearchParams };     // re-export the *type* for consumers