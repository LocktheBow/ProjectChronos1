import { useEffect, useRef, useState } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { fetchRelationships } from '../hooks/useApi';

// Define interfaces locally to avoid import issues
interface GraphNode {
  id: string;
  name: string;
  status: string;
  jurisdiction: string;
  type: 'PRIMARY' | 'SUBSIDIARY';
}

interface GraphLink {
  source: string;
  target: string;
  value: number; // Ownership percentage
}

interface RelationshipGraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

// Status colors from StatusChart.tsx
const STATUS_COLORS: Record<string, string> = {
  PENDING: '#fde047',    // yellow
  ACTIVE: '#4f46e5',     // indigo
  IN_COMPLIANCE: '#10b981', // green
  DELINQUENT: '#ef4444', // red
  DISSOLVED: '#64748b',  // slate
  UNKNOWN: '#94a3b8',    // gray
};

interface RelationshipGraphProps {
  /** Width in pixels or percentage */
  width?: string | number;
  /** Height in pixels */
  height?: number;
  /** Polling interval in ms, set to 0 to disable */
  pollInterval?: number;
}

export default function RelationshipGraph({
  width = '100%',
  height = 500,
  pollInterval = 0
}: RelationshipGraphProps) {
  const [graphData, setGraphData] = useState<RelationshipGraphData | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const graphRef = useRef<any>(null);

  // Fetch relationship data
  useEffect(() => {
    let isMounted = true;
    const controller = new AbortController();

    async function loadData() {
      try {
        setLoading(true);
        const data = await fetchRelationships(controller.signal);
        if (isMounted) {
          setGraphData(data);
          setError(null);
        }
      } catch (err) {
        if (isMounted && (err as DOMException)?.name !== 'AbortError') {
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

  // Node click handler
  const handleNodeClick = (node: GraphNode) => {
    setSelectedNode(node);
    
    // Optionally zoom in on the node
    if (graphRef.current) {
      graphRef.current.centerAt(node.x, node.y, 1000);
      graphRef.current.zoom(2.5, 1000);
    }
  };

  return (
    <div className="relative">
      <div style={{ height: `${height}px`, width }}>
        {graphData && (
          <ForceGraph2D
            ref={graphRef}
            graphData={graphData}
            nodeRelSize={6}
            nodeLabel={(node: any) => `${node.name} (${node.jurisdiction})`}
            nodeColor={(node: any) => STATUS_COLORS[node.status] || STATUS_COLORS.UNKNOWN}
            linkDirectionalArrowLength={3.5}
            linkDirectionalArrowRelPos={1}
            linkLabel={(link: any) => `${link.value}% ownership`}
            onNodeClick={handleNodeClick}
            cooldownTicks={100}
            linkWidth={link => 1.5}
            nodeCanvasObject={(node, ctx, globalScale) => {
              // Node visualization
              const label = node.name;
              const fontSize = 12/globalScale;
              ctx.font = `${fontSize}px Sans-Serif`;
              
              // Draw node circle
              ctx.beginPath();
              ctx.arc(node.x || 0, node.y || 0, 5, 0, 2 * Math.PI);
              ctx.fillStyle = node.color;
              ctx.fill();
              
              // Draw text below the node
              ctx.textAlign = 'center';
              ctx.textBaseline = 'middle';
              ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
              ctx.fillText(label, node.x || 0, (node.y || 0) + 10);
            }}
          />
        )}
        
        {/* Loading overlay */}
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/70">
            <p className="text-gray-500 animate-pulse">Loading relationship data...</p>
          </div>
        )}
        
        {/* Error overlay */}
        {error && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/70">
            <p className="text-red-500">Failed to load relationship data</p>
          </div>
        )}
        
        {/* Empty state */}
        {!loading && !error && graphData && graphData.nodes.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/70">
            <p className="text-gray-500">No relationship data available</p>
          </div>
        )}
      </div>
      
      {/* Entity detail panel */}
      {selectedNode && (
        <div className="absolute top-4 right-4 bg-white p-4 shadow-lg rounded-lg max-w-xs">
          <div className="flex justify-between items-start">
            <h3 className="font-medium">{selectedNode.name}</h3>
            <button 
              className="text-gray-400 hover:text-gray-600" 
              onClick={() => setSelectedNode(null)}
            >
              ×
            </button>
          </div>
          <div className="mt-2 text-sm">
            <p>
              <span className="font-medium">Status:</span>{' '}
              <span 
                className="px-2 py-1 rounded-full text-xs" 
                style={{ 
                  backgroundColor: STATUS_COLORS[selectedNode.status] || STATUS_COLORS.UNKNOWN,
                  color: ['PENDING', 'DISSOLVED'].includes(selectedNode.status) ? '#000' : '#fff' 
                }}
              >
                {selectedNode.status}
              </span>
            </p>
            <p className="mt-1">
              <span className="font-medium">Jurisdiction:</span> {selectedNode.jurisdiction}
            </p>
            <p className="mt-1">
              <span className="font-medium">Type:</span> {selectedNode.type}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}