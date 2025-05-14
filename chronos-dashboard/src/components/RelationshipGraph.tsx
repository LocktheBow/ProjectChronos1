import { useEffect, useRef, useState } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import DebugEntityDetails from './DebugEntityDetails';
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
  const [selectedRawNode, setSelectedRawNode] = useState<any>(null);
  const [showDebugDetails, setShowDebugDetails] = useState(false);
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
      try {
        // Reset zoom and center graph with animation
        // First center at origin
        graphRef.current.centerAt(0, 0, 800);
        
        // Then reset zoom level - staggered for better animation
        setTimeout(() => {
          if (graphRef.current) {
            // Force graph to fit all nodes with some margin
            graphRef.current.zoomToFit(400, 40);
          }
        }, 50);
      } catch (e) {
        console.error("Error resetting zoom:", e);
      }
    }
  };
  
  // Make the method available through the ref
  useEffect(() => {
    if (graphRef.current) {
      graphRef.current.resetZoom = resetZoom;
    }
  }, [graphRef.current]);

  // Node click handler with robust error handling and improved UX
  const handleNodeClick = (node: any) => {
    try {
      console.log("Node clicked:", node);
      
      // Validate that we have a proper node with at least an ID
      if (!node || typeof node !== 'object') {
        console.error("Invalid node clicked:", node);
        return;
      }
      
      // Store the raw node for debugging
      setSelectedRawNode(node);
      
      // Special handling for source/target fields in links that might be nodes themselves
      if (typeof node === 'object' && !node.id && (node.source || node.target)) {
        const sourceNode = typeof node.source === 'object' ? node.source : null;
        const targetNode = typeof node.target === 'object' ? node.target : null;
        
        // Use source or target node if available
        if (sourceNode && sourceNode.id) {
          node = sourceNode;
        } else if (targetNode && targetNode.id) {
          node = targetNode;
        }
      }
      
      // Ensure we have node ID (String version)
      const nodeId = typeof node === 'string' 
        ? node 
        : (node.id || node.__indexColor || node.__graphNodeId || `unknown-${Math.random().toString(36).substring(2, 9)}`);
      
      // Try to find matching node data from filteredGraphData if available
      let matchedNode: GraphNode | undefined;
      if (filteredGraphData?.nodes) {
        matchedNode = filteredGraphData.nodes.find(
          n => n.id === nodeId || n.id === node.id
        );
      }
      
      // Ensure we have all the required properties for display using the best available data
      const enhancedNode: GraphNode = {
        id: nodeId,
        name: matchedNode?.name || node.name || (typeof node.id === 'string' ? node.id : `Entity ${nodeId}`),
        status: matchedNode?.status || node.status || "UNKNOWN",
        jurisdiction: matchedNode?.jurisdiction || node.jurisdiction || "N/A",
        type: matchedNode?.type || node.type || "PRIMARY"
      };
      
      // Log the enhanced node for debugging
      console.log("Enhanced node for display:", enhancedNode);
      
      // If clicking the same node again, toggle the panel off
      if (selectedNode && selectedNode.id === enhancedNode.id) {
        console.log("Toggling off selected node");
        setSelectedNode(null);
        return;
      }
      
      // Set the selected node with all properties ensured
      setSelectedNode(enhancedNode);
      
      // Optionally zoom in on the node if needed
      if (graphRef.current && typeof node.x === 'number' && typeof node.y === 'number') {
        try {
          // Use a shorter animation time for better responsiveness
          graphRef.current.centerAt(node.x, node.y, 500);
          
          // Less aggressive zoom for better context
          setTimeout(() => {
            if (graphRef.current) {
              graphRef.current.zoom(1.8, 500);
            }
          }, 50);
        } catch (zoomErr) {
          console.error("Error zooming to node:", zoomErr);
        }
      }
      
      // Show debug panel on Alt+Click
      try {
        // Check for modifier keys to trigger debug view
        const event = window.event as any;
        if (event && (event.altKey || event.metaKey)) {
          setShowDebugDetails(true);
        }
      } catch (eventErr) {
        console.error("Error checking modifier keys:", eventErr);
      }
    } catch (err) {
      console.error("Error in node click handler:", err);
      // Create a fallback node as a last resort
      setSelectedNode({
        id: typeof node === 'string' ? node : 'unknown',
        name: 'Unknown Entity',
        status: 'UNKNOWN',
        jurisdiction: 'N/A',
        type: 'PRIMARY'
      });
    }
  };

  return (
    <div className="relative">
      {/* Debug tools */}
      {showDebugDetails && selectedRawNode && (
        <DebugEntityDetails 
          node={selectedRawNode} 
          onClose={() => setShowDebugDetails(false)}
        />
      )}
      
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
            linkDistance={80}
            backgroundColor="#ffffff"
            nodeCanvasObject={(node: any, ctx, globalScale) => {
              // Node visualization
              const label = node.name;
              
              // Adaptive font sizing based on zoom level
              // Text only becomes visible when zoomed in enough
              const minScale = 0.7; // Minimum zoom level to start showing text
              const showText = globalScale >= minScale;
              
              // When we zoom in more, text gets relatively smaller to reduce clutter
              // This provides a more stable text size during zooming
              const fontSize = showText ? Math.min(12, 10/globalScale) : 0;
              ctx.font = `${fontSize}px Sans-Serif`;
              
              // Adaptive node size - slightly larger when zoomed out for better visibility
              const baseSize = node.type === 'PRIMARY' ? 8 : 6;
              const size = baseSize / Math.max(0.5, Math.min(1, globalScale));
              
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
              
              // Draw text below the node if showLabels is true and zoom level is appropriate
              if (showLabels && showText) {
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                
                // Move text further down to avoid overlap
                const nameYOffset = 16; // Increased from 12
                const statusYOffset = 32; // Increased from 26
                
                // Create very transparent background for text to ensure visibility in any mode
                const textWidth = ctx.measureText(label).width;
                ctx.fillStyle = 'rgba(255, 255, 255, 0.3)';
                ctx.fillRect(
                  (node.x || 0) - textWidth/2 - 2,
                  (node.y || 0) + nameYOffset - fontSize/2,
                  textWidth + 4,
                  fontSize + 2
                );
                
                ctx.fillStyle = 'rgba(0, 0, 0, 0.9)';
                ctx.fillText(label, node.x || 0, (node.y || 0) + nameYOffset);
                
                // Only show status on higher zoom levels to reduce clutter
                const showStatus = globalScale >= 0.9;
                
                if (showStatus) {
                  // Draw status indicator
                  const statusLabel = node.status.split('_').join(' ');
                  ctx.font = `${fontSize * 0.8}px Sans-Serif`;
                  
                  // Create very transparent background for status text
                  const statusWidth = ctx.measureText(statusLabel).width;
                  ctx.fillStyle = 'rgba(255, 255, 255, 0.3)';
                  ctx.fillRect(
                    (node.x || 0) - statusWidth/2 - 2,
                    (node.y || 0) + statusYOffset - (fontSize * 0.8)/2,
                    statusWidth + 4,
                    (fontSize * 0.8) + 2
                  );
                  
                  ctx.fillStyle = 'rgba(0, 0, 0, 0.8)';
                  ctx.fillText(statusLabel, node.x || 0, (node.y || 0) + statusYOffset);
                }
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
      
      {/* Entity detail panel - positioned using absolute coordinates */}
      {selectedNode && (
        <div 
          className="fixed top-[160px] left-[20px] bg-white p-4 shadow-xl rounded-lg border-l-4 z-[9999] overflow-y-auto" 
          style={{ 
            borderLeftColor: STATUS_COLORS[selectedNode.status] || STATUS_COLORS.UNKNOWN,
            width: '300px', // Fixed width
            maxHeight: 'calc(100vh - 220px)', // Adjust max height to viewport
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)', // Stronger shadow for visibility
            pointerEvents: 'auto', // Ensure clickable
            backdropFilter: 'blur(2px)', // Slight blur for background
            backgroundColor: 'rgba(255, 255, 255, 0.98)' // Nearly opaque background
          }}
        >
          <div className="flex justify-between items-start mb-2">
            <h3 className="font-semibold text-lg">{selectedNode.name}</h3>
            <button 
              className="text-gray-400 hover:text-gray-600 text-xl font-bold" 
              onClick={() => setSelectedNode(null)}
            >
              ×
            </button>
          </div>
          
          {/* Entity information panel */}
          <div className="mt-3 text-sm space-y-2 border-b pb-3 mb-3">
            <div className="flex items-start">
              <span className="font-medium w-24 shrink-0">ID:</span>
              <span className="text-xs text-gray-500 truncate max-w-[200px] break-all">{selectedNode.id}</span>
            </div>
            <div className="flex items-center">
              <span className="font-medium w-24 shrink-0">Status:</span>
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
              <span className="font-medium w-24 shrink-0">Jurisdiction:</span> 
              <span>{selectedNode.jurisdiction}</span>
            </div>
            <div className="flex items-center">
              <span className="font-medium w-24 shrink-0">Type:</span> 
              <span>{selectedNode.type}</span>
            </div>
            
            {/* Debug options for developers */}
            <div className="mt-2 text-xs text-gray-400">
              <button 
                onClick={() => setShowDebugDetails(true)}
                className="underline hover:text-gray-600"
              >
                Show raw data
              </button>
            </div>
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
      )}
    </div>
  );
}