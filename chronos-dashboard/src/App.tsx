import { useEffect, useState } from "react";
import { Bar } from "react-chartjs-2";
import {
  Chart as ChartJS,
  BarElement,
  CategoryScale,
  LinearScale,
  Tooltip,
} from "chart.js";

ChartJS.register(BarElement, CategoryScale, LinearScale, Tooltip);

type Counts = Record<string, number>;

export default function App() {
  const [data, setData] = useState<Counts>({});

  useEffect(() => {
    fetch("http://127.0.0.1:8001/status")
      .then((r) => r.json())
      .then(setData)
      .catch(console.error);
  }, []);

  const labels = Object.keys(data);
  const counts = Object.values(data);

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col items-center p-6">
      <h1 className="text-2xl font-bold mb-4">Chronos Status Dashboard</h1>
      <div className="w-full max-w-xl bg-white shadow p-4 rounded">
        <Bar
          data={{
            labels,
            datasets: [{ label: "Entity count", data: counts }],
          }}
        />
      </div>
    </div>
  );
}
