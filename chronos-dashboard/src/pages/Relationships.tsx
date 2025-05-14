import { useState, useRef } from 'react';
import RelationshipGraph from '../components/RelationshipGraph';
import ShellDetection from '../components/ShellDetection';

const POLL_INTERVAL = 15000; // 15 seconds

export default function Relationships() {
  const [showShellDetection, setShowShellDetection] = useState(true);
  const [showLabels, setShowLabels] = useState(true);
  const [showArrows, setShowArrows] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');
  const graphRef = useRef<any>(null);
  
  // Reset zoom to default view
  const handleResetZoom = () => {
    if (graphRef.current?.resetZoom) {
      graphRef.current.resetZoom();
    }
  };
  
  // Toggle fullscreen
  const handleFullScreen = () => {
    const container = document.querySelector('.graph-container');
    if (!container) return;
    
    if (!document.fullscreenElement) {
      container.requestFullscreen().catch(err => {
        console.error(`Error attempting to enable fullscreen: ${err.message}`);
      });
      // Add fullscreen class for styling
      container.classList.add('fullscreen-mode');
    } else {
      document.exitFullscreen();
      // Remove fullscreen class when exiting
      container.classList.remove('fullscreen-mode');
    }
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-gray-900 mb-2">Corporate Relationship Analysis</h1>
        <p className="text-gray-600">
          Visualize ownership structures and identify potential shell companies
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Main graph area */}
        <div className="lg:col-span-3">
          <div className="bg-white shadow rounded-lg p-6 mb-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-medium text-gray-900">Ownership Network</h2>
              <div className="flex gap-2">
                <button 
                  className="px-3 py-1 bg-white border border-gray-300 rounded text-sm hover:bg-[#F9FAFB]"
                  onClick={handleResetZoom}
                >
                  Reset Zoom
                </button>
                <button 
                  className="px-3 py-1 bg-white border border-gray-300 rounded text-sm hover:bg-[#F9FAFB]"
                  onClick={handleFullScreen}
                >
                  Full Screen
                </button>
              </div>
            </div>
            <p className="text-sm text-gray-600 mb-4">
              Interactive visualization of corporate ownership relationships. Click on any entity to see details.
            </p>
            <div className="mt-4 graph-container bg-white">
              <RelationshipGraph 
                height={600} 
                pollInterval={POLL_INTERVAL}
                showLabels={showLabels}
                showArrows={showArrows}
                statusFilter={statusFilter}
                graphRef={graphRef}
              />
            </div>
            <div className="mt-4 text-xs text-gray-500 flex flex-wrap gap-4">
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
        </div>

        {/* Sidebar */}
        <div>
          {/* Controls */}
          <div className="bg-white shadow rounded-lg p-4 mb-6">
            <h3 className="font-medium text-gray-900 mb-3">Graph Controls</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-sm text-gray-600 mb-1">Display Options</label>
                <div className="flex items-center">
                  <input 
                    type="checkbox" 
                    id="showLabels" 
                    className="mr-2" 
                    checked={showLabels}
                    onChange={(e) => setShowLabels(e.target.checked)}
                  />
                  <label htmlFor="showLabels" className="text-sm">Show Labels</label>
                </div>
                <div className="flex items-center mt-1">
                  <input 
                    type="checkbox" 
                    id="showArrows" 
                    className="mr-2" 
                    checked={showArrows}
                    onChange={(e) => setShowArrows(e.target.checked)}
                  />
                  <label htmlFor="showArrows" className="text-sm">Show Arrows</label>
                </div>
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">Filter by Status</label>
                <select 
                  className="w-full text-sm border border-gray-300 rounded px-2 py-1"
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                >
                  <option value="">All Statuses</option>
                  <option value="ACTIVE">Active</option>
                  <option value="PENDING">Pending</option>
                  <option value="IN_COMPLIANCE">In Compliance</option>
                  <option value="DELINQUENT">Delinquent</option>
                  <option value="DISSOLVED">Dissolved</option>
                </select>
              </div>
            </div>
          </div>

          {/* Shell detection */}
          <div className="bg-white shadow rounded-lg p-4">
            <div className="flex justify-between items-center mb-3">
              <h3 className="font-medium text-gray-900">Shell Detection</h3>
              <button 
                className="text-xs text-gray-500 hover:text-gray-700"
                onClick={() => setShowShellDetection(!showShellDetection)}
              >
                {showShellDetection ? 'Hide' : 'Show'}
              </button>
            </div>
            {showShellDetection && <ShellDetection pollInterval={POLL_INTERVAL} />}
          </div>
        </div>
      </div>
    </div>
  );
}