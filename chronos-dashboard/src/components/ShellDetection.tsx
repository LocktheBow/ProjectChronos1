import { useEffect, useState } from 'react';
import { fetchShellDetection } from '../hooks/useApi';

// Define ShellCompany interface locally to avoid import issues
interface ShellCompany {
  slug: string;
  name: string;
  risk_score: number;
  factors?: string[]; // Optional list of risk factors
}

interface ShellDetectionProps {
  /** How often to poll for updates (ms) - set to 0 to disable */
  pollInterval?: number;
}

export default function ShellDetection({ pollInterval = 0 }: ShellDetectionProps) {
  const [shellCompanies, setShellCompanies] = useState<ShellCompany[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let isMounted = true;
    const controller = new AbortController();

    async function loadData() {
      try {
        setLoading(true);
        const data = await fetchShellDetection(controller.signal);
        if (isMounted) {
          setShellCompanies(data);
          setError(null);
        }
      } catch (err) {
        if (isMounted && (err as DOMException)?.name !== 'AbortError') {
          console.error("Shell detection error:", err);
          setError(err instanceof Error ? err : new Error(String(err)));
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    loadData();

    // Setup polling if interval is provided
    let intervalId: number | undefined;
    if (pollInterval && pollInterval > 0) {
      intervalId = window.setInterval(loadData, pollInterval);
    }

    return () => {
      isMounted = false;
      controller.abort();
      if (intervalId) clearInterval(intervalId);
    };
  }, [pollInterval]);

  // Function to determine risk badge color
  const getRiskBadgeColor = (score: number) => {
    if (score >= 0.7) return 'bg-red-100 text-red-800';
    if (score >= 0.5) return 'bg-orange-100 text-orange-800';
    return 'bg-yellow-100 text-yellow-800';
  };

  return (
    <div className="bg-white shadow rounded-lg p-4">
      <h2 className="text-lg font-medium text-gray-900 mb-4">Potential Shell Companies</h2>
      
      {loading && <p className="text-gray-500 animate-pulse">Analyzing corporate structure...</p>}
      
      {error && <p className="text-red-500">Failed to load shell detection data</p>}
      
      {!loading && !error && shellCompanies.length === 0 && (
        <p className="text-gray-500">No potential shell companies detected</p>
      )}
      
      {shellCompanies.length > 0 && (
        <div className="space-y-3">
          {shellCompanies.map((company) => (
            <div key={company.slug} className="border rounded-lg p-3">
              <div className="flex justify-between items-start">
                <h3 className="font-medium">{company.name}</h3>
                <span 
                  className={`text-xs font-medium px-2.5 py-0.5 rounded ${getRiskBadgeColor(company.risk_score)}`}
                >
                  Risk: {Math.round(company.risk_score * 100)}%
                </span>
              </div>
              <div className="mt-2">
                {company.factors && company.factors.length > 0 ? (
                  <div className="text-sm text-gray-600">
                    <p className="mb-1">Risk factors:</p>
                    <ul className="list-disc list-inside pl-2">
                      {company.factors.map((factor, idx) => (
                        <li key={idx}>{factor}</li>
                      ))}
                    </ul>
                  </div>
                ) : (
                  <p className="text-sm text-gray-600">
                    This entity shows patterns common to shell companies, including unusual ownership structure
                    and limited operational footprint.
                  </p>
                )}
                <div className="mt-3 flex justify-end">
                  <a 
                    href={`/entities/${company.slug}`} 
                    className="text-sm text-indigo-600 hover:text-indigo-500"
                  >
                    View details →
                  </a>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}