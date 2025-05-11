

import React from "react";
import StatusChart from "../components/StatusChart";

/**
 * Primary application dashboard.
 * Encapsulates page layout & delegates actual data‑viz to child components.
 */
const Dashboard: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-100 p-4">
      <h1 className="text-3xl font-bold text-center mb-8">
        Chronos&nbsp;Status&nbsp;Dashboard
      </h1>

      {/* Main content grid */}
      <div className="max-w-4xl mx-auto bg-white shadow rounded p-6">
        {/* Live bar chart of entity counts by status */}
        <StatusChart />
      </div>
    </div>
  );
};

export default Dashboard;