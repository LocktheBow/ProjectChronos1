import { useStatus } from "../hooks/useApi";
import styles from './StatusChart.module.css';

const STATUS_ORDER = [
  "PENDING",
  "ACTIVE",
  "IN_COMPLIANCE",
  "DELINQUENT",
  "DISSOLVED",
] as const;

type StatusBucket = typeof STATUS_ORDER[number];

// Status display names for UI
const STATUS_LABELS: Record<StatusBucket, string> = {
  "PENDING": "Pending",
  "ACTIVE": "Active",
  "IN_COMPLIANCE": "In Compliance",
  "DELINQUENT": "Delinquent",
  "DISSOLVED": "Dissolved"
};

interface StatusChartProps {
  /** Live counts injected by parent – overrides internal polling. */
  counts?: Record<string, number>;
  /** Polling interval (ms) when `counts` prop not supplied; set to 0 to disable polling */
  pollMs?: number;
  /** Optional title for the chart */
  title?: string;
  /** Optional description for the chart */
  description?: string;
}

export default function StatusChart({
  counts: injectedCounts,
  pollMs,
  title = "Entity Status Distribution",
  description = "Live snapshot of entities by current lifecycle status"
}: StatusChartProps) {
  const pollInterval = injectedCounts ? 0 : pollMs ?? 15_000;
  const { data: liveCounts, isLoading, error } = useStatus(pollInterval);

  // prefer prop override, else hook → fallback empty obj
  const sourceCounts = injectedCounts ?? liveCounts ?? {};
  
  // Merge live counts into a fixed order so bars stay in the same slot
  const finalCounts = STATUS_ORDER.map((status) => Number(sourceCounts[status] ?? 0));
  const total = finalCounts.reduce((a, b) => a + b, 0);
  
  // Calculate max count for percentage calculation
  const maxCount = Math.max(...finalCounts, 1); // Avoid division by zero

  // Status to CSS class mapping
  const getStatusClass = (status: StatusBucket): string => {
    switch(status) {
      case "PENDING": return styles.pending;
      case "ACTIVE": return styles.active;
      case "IN_COMPLIANCE": return styles.inCompliance;
      case "DELINQUENT": return styles.delinquent;
      case "DISSOLVED": return styles.dissolved;
      default: return "";
    }
  };

  return (
    <div className={`${styles.chartContainer} ${isLoading ? styles.loading : ''}`}>
      {title && <h2 className={styles.chartHeader}>{title}</h2>}
      {description && <p className={styles.chartDescription}>{description}</p>}
      
      {error ? (
        <div className={styles.error}>
          Error loading status data
        </div>
      ) : total === 0 && !isLoading ? (
        <div className={styles.error} style={{ color: 'var(--c-slate-500)' }}>
          No portfolio data available
        </div>
      ) : (
        <>
          <div className={styles.barChart}>
            {STATUS_ORDER.map((status, index) => {
              const count = finalCounts[index];
              const percentage = Math.round((count / maxCount) * 100);
              
              return (
                <div className={styles.barGroup} key={status}>
                  <div className={styles.barHeader}>
                    <span className={styles.barLabel}>{STATUS_LABELS[status]}</span>
                    <span className={styles.barCount}>{count}</span>
                  </div>
                  <div className={styles.barWrapper}>
                    <div 
                      className={`${styles.bar} ${getStatusClass(status)}`} 
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
          
          <div className={styles.legend}>
            {STATUS_ORDER.map(status => (
              <div className={styles.legendItem} key={status}>
                <span 
                  className={styles.legendColor} 
                  style={{ backgroundColor: getComputedStyle(document.documentElement).getPropertyValue(`--c-status-${status.toLowerCase().replace('_', '-')}`) }}
                />
                {STATUS_LABELS[status]}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}