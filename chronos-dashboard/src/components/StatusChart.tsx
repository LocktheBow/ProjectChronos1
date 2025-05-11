import { useEffect, useState } from "react";
import {
  Chart as ChartJS,
  BarElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend,
} from "chart.js";
import { Bar } from "react-chartjs-2";

// Register chart.js pieces once at module load
ChartJS.register(BarElement, CategoryScale, LinearScale, Tooltip, Legend);

interface StatusChartProps {
  /** Live counts injected by parent – overrides internal polling. */
  counts?: Record<string, number>;
  /** Polling interval (ms) when `counts` prop not supplied */
  pollMs?: number;
}

export default function StatusChart({
  counts: injectedCounts,
  pollMs = 5000,
}: StatusChartProps) {
  // internal state used only when parent doesn’t pass counts
  const [internalCounts, setInternalCounts] = useState<Record<string, number>>(
    {}
  );

  // If parent didn’t provide counts, start the polling loop
  useEffect(() => {
    if (injectedCounts) return; // parent drives updates
    async function fetchStatus() {
      try {
        const res = await fetch("http://localhost:8001/status");
        if (!res.ok) throw new Error(await res.text());
        setInternalCounts(await res.json());
      } catch (err) {
        /* eslint-disable no-console */
        console.error("status fetch failed:", err);
        /* eslint-enable no-console */
      }
    }
    fetchStatus(); // initial
    const id = setInterval(fetchStatus, pollMs);
    return () => clearInterval(id);
  }, [injectedCounts, pollMs]);

  // Decide which dataset to show
  const sourceCounts = injectedCounts ?? internalCounts;
  const labels = Object.keys(sourceCounts);

  const data = {
    labels,
    datasets: [
      {
        label: "Entities",
        data: labels.map((l) => sourceCounts[l]),
        backgroundColor: "#2b9348",
      },
    ],
  };

  if (labels.length === 0) {
    return (
      <p className="text-center text-sm text-gray-400">
        No entities yet. Add one via the API to see live counts.
      </p>
    );
  }

  return <Bar data={data} />;
}