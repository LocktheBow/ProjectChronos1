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
            nodeRelSize={8}
            nodeLabel={(node: any) => `${node.name} (${node.jurisdiction})\nStatus: ${node.status}`}
            nodeColor={(node: any) => STATUS_COLORS[node.status] || STATUS_COLORS.UNKNOWN}
            linkDirectionalArrowLength={5}
            linkDirectionalArrowRelPos={1}
            linkDirectionalParticles={2}
            linkDirectionalParticleSpeed={0.005}
            linkLabel={(link: any) => `${link.value}% ownership`}
            onNodeClick={handleNodeClick}
            cooldownTicks={100}
            linkWidth={link => 1.5}
            nodeCanvasObject={(node: any, ctx, globalScale) => {
              // Node visualization
              const label = node.name;
              const fontSize = 12/globalScale;
              ctx.font = `${fontSize}px Sans-Serif`;
              
              // Node size based on importance
              const size = node.type === 'PRIMARY' ? 8 : 6;
              
              // Draw node circle
              ctx.beginPath();
              ctx.arc(node.x || 0, node.y || 0, size, 0, 2 * Math.PI);
              ctx.fillStyle = STATUS_COLORS[node.status] || STATUS_COLORS.UNKNOWN;
              ctx.fill();
              
              // Add border for selected node
              if (selectedNode && node.id === selectedNode.id) {
                ctx.beginPath();
                ctx.arc(node.x || 0, node.y || 0, size + 2, 0, 2 * Math.PI);
                ctx.strokeStyle = '#000';
                ctx.lineWidth = 2 / globalScale;
                ctx.stroke();
              }
              
              // Draw text below the node
              ctx.textAlign = 'center';
              ctx.textBaseline = 'middle';
              ctx.fillStyle = 'rgba(0, 0, 0, 0.8)';
              ctx.fillText(label, node.x || 0, (node.y || 0) + 12);
              
              // Draw status indicator
              const statusLabel = node.status.split('_').join(' ');
              ctx.font = `${fontSize * 0.8}px Sans-Serif`;
              ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
              ctx.fillText(statusLabel, node.x || 0, (node.y || 0) + 24);
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
        <div className="absolute top-4 right-4 bg-white p-4 shadow-lg rounded-lg max-w-xs border-l-4" 
             style={{ borderLeftColor: STATUS_COLORS[selectedNode.status] || STATUS_COLORS.UNKNOWN }}>
          <div className="flex justify-between items-start">
            <h3 className="font-semibold text-lg">{selectedNode.name}</h3>
            <button 
              className="text-gray-400 hover:text-gray-600 text-xl font-bold" 
              onClick={() => setSelectedNode(null)}
            >
              ×
            </button>
          </div>
          <div className="mt-3 text-sm space-y-2">
            <div className="flex items-center">
              <span className="font-medium w-24">Status:</span>
              <span 
                className="px-2 py-1 rounded-full text-xs" 
                style={{ 
                  backgroundColor: STATUS_COLORS[selectedNode.status] || STATUS_COLORS.UNKNOWN,
                  color: ['PENDING', 'DISSOLVED'].includes(selectedNode.status) ? '#000' : '#fff' 
                }}
              >
                {selectedNode.status.replace('_', ' ')}
              </span>
            </div>
            <div className="flex items-center">
              <span className="font-medium w-24">Jurisdiction:</span> 
              <span>{selectedNode.jurisdiction}</span>
            </div>
            <div className="flex items-center">
              <span className="font-medium w-24">Type:</span> 
              <span>{selectedNode.type}</span>
            </div>
            
            {/* Relationship details */}
            {graphData && (
              <>
                <div className="mt-4 mb-2">
                  <h4 className="font-medium text-gray-700 border-b pb-1">Relationships</h4>
                </div>
                
                {/* Parent companies */}
                {graphData.links.filter(link => link.target === selectedNode.id).length > 0 && (
                  <div>
                    <span className="font-medium">Owned by:</span>
                    <ul className="list-disc list-inside ml-2 mt-1">
                      {graphData.links
                        .filter(link => link.target === selectedNode.id)
                        .map(link => {
                          const parentNode = graphData.nodes.find(n => n.id === link.source);
                          return (
                            <li key={`parent-${link.source}`} className="text-xs">
                              {parentNode?.name} ({link.value}%)
                            </li>
                          );
                        })}
                    </ul>
                  </div>
                )}
                
                {/* Subsidiary companies */}
                {graphData.links.filter(link => link.source === selectedNode.id).length > 0 && (
                  <div className="mt-2">
                    <span className="font-medium">Owns:</span>
                    <ul className="list-disc list-inside ml-2 mt-1">
                      {graphData.links
                        .filter(link => link.source === selectedNode.id)
                        .map(link => {
                          const subsidNode = graphData.nodes.find(n => n.id === link.target);
                          return (
                            <li key={`subsidiary-${link.target}`} className="text-xs">
                              {subsidNode?.name} ({link.value}%)
                            </li>
                          );
                        })}
                    </ul>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}