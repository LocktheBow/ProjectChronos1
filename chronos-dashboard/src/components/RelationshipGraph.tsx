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
  /** Whether to show node labels */
  showLabels?: boolean;
  /** Whether to show directional arrows */
  showArrows?: boolean;
  /** Status filter for nodes */
  statusFilter?: string;
  /** Ref for accessing the graph instance */
  graphRef?: React.RefObject<any>;
  /** Key that changes to trigger data refresh */
  refreshKey?: number;
}

export default function RelationshipGraph({
  width = '100%',
  height = 500,
  pollInterval = 0,
  showLabels = true,
  showArrows = true,
  statusFilter = '',
  graphRef: externalGraphRef,
  refreshKey = 0
}: RelationshipGraphProps) {
  const [rawGraphData, setRawGraphData] = useState<RelationshipGraphData | null>(null);
  const [filteredGraphData, setFilteredGraphData] = useState<RelationshipGraphData | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const internalGraphRef = useRef<any>(null);
  const graphRef = externalGraphRef || internalGraphRef;

  // Fetch relationship data
  useEffect(() => {
    let isMounted = true;
    const controller = new AbortController();

    async function loadData() {
      try {
        setLoading(true);
        const data = await fetchRelationships(controller.signal);
        if (isMounted) {
          setRawGraphData(data);
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
  }, [pollInterval, refreshKey]);

  // Apply filters when raw data or status filter changes
  useEffect(() => {
    if (!rawGraphData) return;
    
    if (!statusFilter) {
      // No filter, use all data
      setFilteredGraphData(rawGraphData);
      return;
    }
    
    // Filter nodes by status
    const filteredNodes = rawGraphData.nodes.filter(node => 
      node.status === statusFilter
    );
    
    // Get IDs of filtered nodes
    const filteredNodeIds = new Set(filteredNodes.map(node => node.id));
    
    // Filter links that connect filtered nodes
    const filteredLinks = rawGraphData.links.filter(link => 
      filteredNodeIds.has(link.source as string) && filteredNodeIds.has(link.target as string)
    );
    
    setFilteredGraphData({
      nodes: filteredNodes,
      links: filteredLinks
    });
  }, [rawGraphData, statusFilter, showLabels, showArrows]);
  
  // Expose reset zoom method
  const resetZoom = () => {
    if (graphRef.current) {
      graphRef.current.centerAt(0, 0, 1000);
      graphRef.current.zoom(1, 1000);
    }
  };
  
  // Make the method available through the ref
  useEffect(() => {
    if (graphRef.current) {
      graphRef.current.resetZoom = resetZoom;
    }
  }, [graphRef]);

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
      <div style={{ height: `${height}px`, width }} className="bg-white">
        {filteredGraphData && (
          <ForceGraph2D
            ref={graphRef}
            graphData={filteredGraphData}
            nodeRelSize={8}
            nodeLabel={(node: any) => `${node.name} (${node.jurisdiction})\nStatus: ${node.status}`}
            nodeColor={(node: any) => STATUS_COLORS[node.status] || STATUS_COLORS.UNKNOWN}
            linkDirectionalArrowLength={showArrows ? 5 : 0}
            linkDirectionalArrowRelPos={1}
            linkDirectionalParticles={showArrows ? 2 : 0}
            linkDirectionalParticleSpeed={0.005}
            linkLabel={(link: any) => `${link.value}% ownership`}
            onNodeClick={handleNodeClick}
            cooldownTicks={100}
            linkWidth={link => 2}
            d3AlphaDecay={0.02}
            d3VelocityDecay={0.3}
            dagMode={null}
            dagLevelDistance={50}
            backgroundColor="#ffffff"
            nodeCanvasObject={(node: any, ctx, globalScale) => {
              // Node visualization
              const label = node.name;
              const fontSize = 12/globalScale;
              ctx.font = `${fontSize}px Sans-Serif`;
              
              // Node size based on importance
              const size = node.type === 'PRIMARY' ? 10 : 7;
              
              // Draw node circle
              ctx.beginPath();
              ctx.arc(node.x || 0, node.y || 0, size, 0, 2 * Math.PI);
              ctx.fillStyle = STATUS_COLORS[node.status] || STATUS_COLORS.UNKNOWN;
              ctx.fill();
              
              // Highlight selected node with slightly larger size instead of border
              if (selectedNode && node.id === selectedNode.id) {
                // Just make the node slightly larger when selected
                ctx.beginPath();
                ctx.arc(node.x || 0, node.y || 0, size * 1.2, 0, 2 * Math.PI);
                ctx.fillStyle = STATUS_COLORS[node.status] || STATUS_COLORS.UNKNOWN;
                ctx.fill();
              }
              
              // Draw text below the node if showLabels is true
              if (showLabels) {
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                
                // Create solid background for text to ensure visibility in any mode
                const textWidth = ctx.measureText(label).width;
                ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
                ctx.fillRect(
                  (node.x || 0) - textWidth/2 - 4,
                  (node.y || 0) + 12 - fontSize/2 - 1,
                  textWidth + 8,
                  fontSize + 4
                );
                
                // Add a border around the label background
                ctx.strokeStyle = 'rgba(220, 220, 220, 0.8)';
                ctx.lineWidth = 1 / globalScale;
                ctx.strokeRect(
                  (node.x || 0) - textWidth/2 - 4,
                  (node.y || 0) + 12 - fontSize/2 - 1,
                  textWidth + 8,
                  fontSize + 4
                );
                
                ctx.fillStyle = 'rgba(0, 0, 0, 0.9)';
                ctx.fillText(label, node.x || 0, (node.y || 0) + 12);
                
                // Draw status indicator
                const statusLabel = node.status.split('_').join(' ');
                ctx.font = `${fontSize * 0.8}px Sans-Serif`;
                
                // Create solid background for status text
                const statusWidth = ctx.measureText(statusLabel).width;
                ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
                ctx.fillRect(
                  (node.x || 0) - statusWidth/2 - 4,
                  (node.y || 0) + 26 - (fontSize * 0.8)/2 - 1,
                  statusWidth + 8,
                  (fontSize * 0.8) + 4
                );
                
                // Add a border around the status background
                ctx.strokeStyle = 'rgba(220, 220, 220, 0.8)';
                ctx.lineWidth = 1 / globalScale;
                ctx.strokeRect(
                  (node.x || 0) - statusWidth/2 - 4,
                  (node.y || 0) + 26 - (fontSize * 0.8)/2 - 1,
                  statusWidth + 8,
                  (fontSize * 0.8) + 4
                );
                
                ctx.fillStyle = 'rgba(0, 0, 0, 0.8)';
                ctx.fillText(statusLabel, node.x || 0, (node.y || 0) + 26);
              }
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
        {!loading && !error && filteredGraphData && filteredGraphData.nodes.length === 0 && (
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
            {filteredGraphData && (
              <>
                <div className="mt-4 mb-2">
                  <h4 className="font-medium text-gray-700 border-b pb-1">Relationships</h4>
                </div>
                
                {/* Parent companies */}
                {filteredGraphData.links.filter(link => link.target === selectedNode.id).length > 0 && (
                  <div>
                    <span className="font-medium">Owned by:</span>
                    <ul className="list-disc list-inside ml-2 mt-1">
                      {filteredGraphData.links
                        .filter(link => link.target === selectedNode.id)
                        .map(link => {
                          const parentNode = filteredGraphData.nodes.find(n => n.id === link.source);
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
                {filteredGraphData.links.filter(link => link.source === selectedNode.id).length > 0 && (
                  <div className="mt-2">
                    <span className="font-medium">Owns:</span>
                    <ul className="list-disc list-inside ml-2 mt-1">
                      {filteredGraphData.links
                        .filter(link => link.source === selectedNode.id)
                        .map(link => {
                          const subsidNode = filteredGraphData.nodes.find(n => n.id === link.target);
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