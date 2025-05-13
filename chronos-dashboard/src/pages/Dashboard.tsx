

import { useState } from 'react';
import StatusChart from '../components/StatusChart';
import RelationshipGraph from '../components/RelationshipGraph';
import ShellDetection from '../components/ShellDetection';

const POLL_INTERVAL = 15000; // 15 seconds

/**
 * Primary application dashboard.
 * Encapsulates page layout & delegates actual data-viz to child components.
 */
const Dashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'overview' | 'relationships' | 'analysis'>('overview');

  return (
    <div className="min-h-screen bg-gray-100 p-4">
      <h1 className="text-3xl font-bold text-center mb-6">
        Chronos&nbsp;Status&nbsp;Dashboard
      </h1>
      <p className="text-gray-600 text-center mb-8">Monitor and analyze your corporate portfolio</p>

      {/* Tabs */}
      <div className="max-w-6xl mx-auto border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8 justify-center">
          <button
            onClick={() => setActiveTab('overview')}
            className={`pb-3 px-1 font-medium text-sm border-b-2 ${
              activeTab === 'overview'
                ? 'border-indigo-500 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Overview
          </button>
          <button
            onClick={() => setActiveTab('relationships')}
            className={`pb-3 px-1 font-medium text-sm border-b-2 ${
              activeTab === 'relationships'
                ? 'border-indigo-500 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Relationships
          </button>
          <button
            onClick={() => setActiveTab('analysis')}
            className={`pb-3 px-1 font-medium text-sm border-b-2 ${
              activeTab === 'analysis'
                ? 'border-indigo-500 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Risk Analysis
          </button>
        </nav>
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div className="max-w-4xl mx-auto bg-white shadow rounded p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Status Snapshot</h2>
          <StatusChart pollMs={POLL_INTERVAL} />
        </div>
      )}

      {/* Relationships Tab */}
      {activeTab === 'relationships' && (
        <div className="max-w-6xl mx-auto bg-white shadow rounded p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Corporate Relationship Network</h2>
          <p className="text-sm text-gray-600 mb-4">
            This graph visualizes the ownership relationships between entities in your portfolio.
            Colors indicate entity status, arrows show ownership direction.
          </p>
          <div className="mt-4">
            <RelationshipGraph height={600} pollInterval={POLL_INTERVAL} />
          </div>
          <div className="mt-4 text-xs text-gray-500 flex flex-wrap gap-4 justify-center">
            <div className="flex items-center">
              <span className="w-3 h-3 inline-block mr-1 rounded-full bg-[#fde047]"></span> Pending
            </div>
            <div className="flex items-center">
              <span className="w-3 h-3 inline-block mr-1 rounded-full bg-[#4f46e5]"></span> Active
            </div>
            <div className="flex items-center">
              <span className="w-3 h-3 inline-block mr-1 rounded-full bg-[#10b981]"></span> In Compliance
            </div>
            <div className="flex items-center">
              <span className="w-3 h-3 inline-block mr-1 rounded-full bg-[#ef4444]"></span> Delinquent
            </div>
            <div className="flex items-center">
              <span className="w-3 h-3 inline-block mr-1 rounded-full bg-[#64748b]"></span> Dissolved
            </div>
          </div>
        </div>
      )}

      {/* Analysis Tab */}
      {activeTab === 'analysis' && (
        <div className="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <div className="bg-white shadow rounded p-6">
              <h2 className="text-lg font-medium text-gray-900 mb-4">Risk Overview</h2>
              <p className="text-sm text-gray-600 mb-4">
                Our algorithm analyzes corporate structures to identify potential shell companies and
                suspicious ownership patterns based on multiple risk factors.
              </p>
              <div className="mt-6">
                <h3 className="font-medium text-gray-900 mb-2">Risk Factors:</h3>
                <ul className="list-disc pl-5 text-sm text-gray-600 space-y-2">
                  <li>Entities with no subsidiaries but owned by other companies</li>
                  <li>Entities in chains of single-child ownership</li>
                  <li>Active entities with minimal operational footprint</li>
                  <li>Entities that share registered agents or addresses</li>
                  <li>Cross-ownership patterns indicating potential circular structures</li>
                </ul>
              </div>
            </div>
          </div>
          <div>
            <ShellDetection pollInterval={POLL_INTERVAL} />
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;