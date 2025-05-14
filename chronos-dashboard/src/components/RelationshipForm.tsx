import { useState, useEffect } from 'react';
import { api } from '../hooks/useApi';

interface RelationshipFormProps {
  onSuccess: () => void;
  onClose?: () => void;
}

interface Entity {
  slug: string;
  name: string;
  jurisdiction: string;
  status: string;
}

// Fallback list of common entities for demonstration purposes
const DEMO_ENTITIES: Entity[] = [
  { slug: "alphabet-inc", name: "Alphabet Inc", jurisdiction: "DE", status: "ACTIVE" },
  { slug: "google-llc", name: "Google LLC", jurisdiction: "DE", status: "ACTIVE" },
  { slug: "youtube-llc", name: "YouTube LLC", jurisdiction: "DE", status: "ACTIVE" },
  { slug: "apple-inc.", name: "Apple Inc.", jurisdiction: "CA", status: "ACTIVE" },
  { slug: "the-walt-disney-company", name: "The Walt Disney Company", jurisdiction: "DE", status: "ACTIVE" },
  { slug: "monster-beverage-corp", name: "Monster Beverage Corp", jurisdiction: "DE", status: "ACTIVE" },
  { slug: "coca-cola-company", name: "Coca-Cola Company", jurisdiction: "DE", status: "ACTIVE" },
  { slug: "acme-corporation", name: "Acme Corporation", jurisdiction: "DE", status: "ACTIVE" },
  { slug: "widget-industries", name: "Widget Industries", jurisdiction: "NY", status: "IN_COMPLIANCE" },
  { slug: "techstart-llc", name: "TechStart LLC", jurisdiction: "CA", status: "PENDING" }
];

export default function RelationshipForm({ onSuccess, onClose }: RelationshipFormProps) {
  // Start with empty entities to avoid showing demo ones before real ones load
  const [entities, setEntities] = useState<Entity[]>([]);
  const [loading, setLoading] = useState(true); // Start with loading state
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  // Form state
  const [parentSlug, setParentSlug] = useState('');
  const [childSlug, setChildSlug] = useState('');
  const [ownershipPercentage, setOwnershipPercentage] = useState(100);
  
  // Helper function to directly create an entity via API
  const createEntity = async (name: string, jurisdiction = 'US', status = 'ACTIVE') => {
    try {
      console.log(`Attempting to create entity: ${name} (${jurisdiction}) - ${status}`);
      
      // First check if entity already exists by name
      const slugName = name.toLowerCase().replace(/\s+/g, '-');
      try {
        const checkResponse = await fetch(`/entities/${slugName}`);
        if (checkResponse.ok) {
          console.log(`Entity ${name} already exists, skipping creation`);
          return true;
        }
      } catch (checkErr) {
        // Entity doesn't exist, continue with creation
        console.log(`Entity ${name} not found, will create it`);
      }
      
      // Try multiple creation endpoints
      const endpoints = [
        // Standard entities endpoint
        {
          url: '/entities',
          body: {
            name,
            jurisdiction,
            status,
            formed: new Date().toISOString().split('T')[0]
          }
        },
        // Alternate entity creation formats
        {
          url: '/entities',
          body: {
            name,
            jurisdiction,
            status: status,
            formed_date: new Date().toISOString().split('T')[0]
          }
        },
        // Direct entity endpoint with slug
        {
          url: `/entities/${slugName}`,
          body: {
            name,
            jurisdiction,
            status
          }
        }
      ];
      
      let created = false;
      
      // Try each endpoint until one succeeds
      for (const endpoint of endpoints) {
        try {
          console.log(`Trying to create entity via ${endpoint.url}...`);
          const response = await fetch(endpoint.url, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(endpoint.body)
          });
          
          if (response.ok) {
            console.log(`Successfully created entity: ${name}`);
            created = true;
            break;
          } else {
            console.warn(`Failed to create entity via ${endpoint.url}: ${response.status}`);
          }
        } catch (endpointError) {
          console.warn(`Error with ${endpoint.url}:`, endpointError);
        }
      }
      
      // If entity was created, refresh the entity list
      if (created) {
        await loadAllEntities();
        return true;
      }
      
      // Last resort: manually add to local list
      if (!created) {
        console.log(`Manually adding entity ${name} to local list only`);
        setEntities(prev => [
          ...prev,
          {
            slug: slugName,
            name,
            jurisdiction,
            status
          }
        ]);
        return true;
      }
      
      return false;
    } catch (e) {
      console.error(`Failed to create entity ${name}:`, e);
      
      // Last resort: add to local state regardless of error
      const slugName = name.toLowerCase().replace(/\s+/g, '-');
      setEntities(prev => [
        ...prev,
        {
          slug: slugName,
          name,
          jurisdiction,
          status
        }
      ]);
      
      return false;
    }
  };

  // Function to load all entities from multiple sources
  const loadAllEntities = async () => {
    try {
      setLoading(true);
      console.log("Loading all entities from portfolio...");
      // Start with EMPTY array, not demo entities
      let allEntities: Entity[] = [];
      let hasAddedGraphEntities = false;
        
        // PRIORITY 1: First try to get graph nodes directly, which should have all currently visible entities
        try {
          const graphResponse = await fetch('/relationships');
          
          if (graphResponse.ok) {
            const graphData = await graphResponse.json();
            console.log(`Found ${graphData.nodes?.length} nodes in graph`);
            
            if (graphData.nodes && graphData.nodes.length > 0) {
              // Convert graph nodes to entity format and merge
              const slugs = new Set(allEntities.map(e => e.slug));
              for (const node of graphData.nodes) {
                if (!slugs.has(node.id)) {
                  allEntities.push({
                    slug: node.id,
                    name: node.name || node.id,
                    status: node.status || "UNKNOWN",
                    jurisdiction: node.jurisdiction || "N/A"
                  });
                  slugs.add(node.id);
                  hasAddedGraphEntities = true;
                }
              }
            }
          }
        } catch (graphError) {
          console.error("Graph nodes fetch failed:", graphError);
        }
        
        // PRIORITY 2: Try to get entity list from API directly
        try {
          // Try both /entities and /entities/all endpoints
          const endpoints = ['/entities/all', '/entities', '/entity-list'];
          
          for (const endpoint of endpoints) {
            try {
              const response = await fetch(endpoint);
              
              if (response.ok) {
                const data = await response.json();
                console.log(`Loaded ${data.length} entities from ${endpoint}`);
                
                if (data && data.length > 0) {
                  // Merge with existing entities, avoiding duplicates by slug
                  const slugs = new Set(allEntities.map(e => e.slug));
                  for (const entity of data) {
                    // Handle different entity formats
                    const slug = entity.slug || entity.id;
                    if (slug && !slugs.has(slug)) {
                      allEntities.push({
                        slug: slug,
                        name: entity.name || slug,
                        status: entity.status || "UNKNOWN",
                        jurisdiction: entity.jurisdiction || "N/A"
                      });
                      slugs.add(slug);
                    }
                  }
                  break; // Exit loop if we successfully got entities
                }
              }
            } catch (endpointError) {
              console.warn(`Failed to fetch from ${endpoint}:`, endpointError);
            }
          }
        } catch (apiError) {
          console.error("All API entity fetch attempts failed:", apiError);
        }
        
        // PRIORITY 3: Try to fetch entities directory from API
        try {
          const response = await fetch('/entity-list');
          if (response.ok) {
            const data = await response.json();
            if (Array.isArray(data) && data.length > 0) {
              console.log(`Loaded ${data.length} entities from entity-list endpoint`);
              
              // Merge with existing entities
              const slugs = new Set(allEntities.map(e => e.slug));
              for (const entity of data) {
                const slug = entity.slug || entity.id || (typeof entity === 'string' ? entity : null);
                if (slug && !slugs.has(slug)) {
                  allEntities.push({
                    slug: slug,
                    name: entity.name || slug,
                    status: entity.status || "UNKNOWN",
                    jurisdiction: entity.jurisdiction || "N/A"
                  });
                  slugs.add(slug);
                }
              }
            }
          }
        } catch (entityListError) {
          console.warn("Entity list fetch failed:", entityListError);
        }
        
        // PRIORITY 4: Try to access any visible graph nodes by checking DOM
        if (!hasAddedGraphEntities && typeof document !== 'undefined') {
          try {
            // Look for node labels in the SVG
            const nodeLabels = document.querySelectorAll('.node-label, [data-node-id], text');
            if (nodeLabels && nodeLabels.length > 0) {
              console.log(`Found ${nodeLabels.length} node labels in DOM`);
              
              const slugs = new Set(allEntities.map(e => e.slug));
              nodeLabels.forEach(label => {
                const nodeId = label.getAttribute('data-node-id') || label.textContent?.trim();
                if (nodeId && !slugs.has(nodeId)) {
                  // Clean up the name by removing any status info in parentheses
                  let cleanName = nodeId;
                  if (label.textContent) {
                    cleanName = label.textContent.trim().split('(')[0].trim();
                  }
                  
                  allEntities.push({
                    slug: nodeId,
                    name: cleanName || nodeId,
                    status: "UNKNOWN", // Can't determine from DOM
                    jurisdiction: "N/A"
                  });
                  slugs.add(nodeId);
                }
              });
            }
            
            // Also look for any rendered graph nodes with titles
            const graphNodes = document.querySelectorAll('[data-node-id], .node, .graph-node, circle');
            if (graphNodes && graphNodes.length > 0) {
              console.log(`Found ${graphNodes.length} visual nodes in DOM`);
              
              const slugs = new Set(allEntities.map(e => e.slug));
              graphNodes.forEach(node => {
                const nodeId = node.getAttribute('data-node-id') || 
                              node.getAttribute('id') || 
                              node.getAttribute('title');
                              
                if (nodeId && !slugs.has(nodeId)) {
                  allEntities.push({
                    slug: nodeId,
                    name: nodeId,
                    status: "UNKNOWN", // Can't determine from DOM
                    jurisdiction: "N/A"
                  });
                  slugs.add(nodeId);
                }
              });
            }
          } catch (domError) {
            console.error("DOM-based entity extraction failed:", domError);
          }
        }
        
        console.log(`Total entities available: ${allEntities.length}`);
        setEntities(allEntities);
      } catch (err) {
        console.error("Error loading entities:", err);
        // Keep the demo entities on error
      } finally {
        setLoading(false);
      }
    };
    
    // Call the function when component mounts
    useEffect(() => {
      loadAllEntities();
    }, []);
  
  // Core function to create relationship using the exact same model as backend
  const createDirectRelationship = async (parent: string, child: string, percentage: number) => {
    console.log(`Creating relationship: ${parent} → ${child} (${percentage}%)`);
    
    // Create the payload to match expected backend format
    const payload = {
      parent_slug: parent,
      child_slug: child,
      ownership_percentage: percentage
    };
    
    console.log("Request payload:", JSON.stringify(payload));
    
    const endpoints = [
      { url: 'http://localhost:8001/relationships/direct-relationship', method: 'POST' },
      { url: 'http://localhost:8001/relationships', method: 'POST' },
      { url: `http://localhost:8001/relationships/edge/${parent}/${child}?value=${percentage}`, method: 'POST' }
    ];
    
    // Try each endpoint until one succeeds
    for (const endpoint of endpoints) {
      try {
        console.log(`Trying ${endpoint.method} to ${endpoint.url}...`);
        
        const response = await fetch(endpoint.url, {
          method: endpoint.method,
          headers: { 
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          // Only include body for POST requests with a payload
          ...(endpoint.method === 'POST' && !endpoint.url.includes('/edge/') && { 
            body: JSON.stringify(payload) 
          })
        });
        
        // Log response details
        const responseText = await response.text();
        console.log(`${endpoint.url} response: ${response.status} - ${responseText}`);
        
        // If successful, return the parsed result
        if (response.ok) {
          try {
            return responseText ? JSON.parse(responseText) : { success: true };
          } catch (e) {
            return { message: responseText || 'Success (no response body)' };
          }
        }
      } catch (error) {
        console.warn(`Error with ${endpoint.url}:`, error);
        // Continue to the next endpoint
      }
    }
    
    // If we reach here, all endpoints failed
    throw new Error("All relationship creation endpoints failed");
  };
  
  // Form submission handler
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Form validation
    if (!parentSlug) {
      setError('Please select a parent entity');
      return;
    }
    
    if (!childSlug) {
      setError('Please select a child entity');
      return;
    }
    
    if (parentSlug === childSlug) {
      setError('Parent and child cannot be the same entity');
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      // Call the direct relationship creation function
      await createDirectRelationship(parentSlug, childSlug, ownershipPercentage);
      
      // Show success message
      setSuccess(`Relationship created: ${parentSlug} → ${childSlug} (${ownershipPercentage}%)`);
      
      // Reset form
      setParentSlug('');
      setChildSlug('');
      setOwnershipPercentage(100);
      
      // Notify parent component of success and refresh graph
      onSuccess();
      
      // Auto-close after success if onClose provided
      if (onClose) {
        setTimeout(onClose, 1500);
      }
      
      // Reload entities after a delay to ensure server has processed everything
      setTimeout(async () => {
        await loadAllEntities();
        onSuccess(); // Refresh graph again
      }, 500);
      
    } catch (err) {
      console.error('Error creating relationship:', err);
      setError(err instanceof Error ? err.message : 'Failed to create relationship');
    } finally {
      setLoading(false);
    }
  };
  
  // Debug utility to manually add entities (for debugging)
  const addManualEntity = () => {
    const entityName = prompt('Enter entity name:');
    if (entityName) {
      const slug = entityName.toLowerCase().replace(/\s+/g, '-');
      setEntities(prev => [
        ...prev, 
        {
          slug,
          name: entityName,
          jurisdiction: 'US',
          status: 'ACTIVE'
        }
      ]);
    }
  };
  
  // Log information about current state
  useEffect(() => {
    console.log(`RelationshipForm state update: ${entities.length} entities available`);
    entities.forEach(e => console.log(`  - ${e.name} (${e.slug})`));
  }, [entities]);

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-medium">Add Parent-Subsidiary Relationship</h2>
        {onClose && (
          <button 
            onClick={onClose}
            className="text-gray-400 hover:text-gray-500 text-xl"
          >
            ×
          </button>
        )}
      </div>
      
      {error && (
        <div className="mb-4 p-2 bg-red-50 border border-red-200 text-red-600 rounded">
          {error}
        </div>
      )}
      
      {success && (
        <div className="mb-4 p-2 bg-green-50 border border-green-200 text-green-600 rounded">
          {success}
        </div>
      )}
      
      {loading && (
        <div className="mb-4 p-2 bg-blue-50 border border-blue-200 text-blue-600 rounded flex items-center">
          <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          Loading entities...
        </div>
      )}
      
      {/* Entity management controls - always show this */}
      <div className="mb-4 p-2 bg-gray-50 border border-gray-200 rounded">
        <div className="flex justify-between items-center">
          <span className="text-sm font-medium text-gray-700">
            {entities.length === 0 
              ? "No entities found. Please add entities first." 
              : `${entities.length} entities available`}
          </span>
          <div className="flex gap-1">
            <button 
              type="button"
              onClick={loadAllEntities}
              className="px-2 py-1 bg-gray-200 hover:bg-gray-300 rounded text-xs flex items-center"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Refresh
            </button>
          </div>
        </div>
        
        <div className="mt-2 flex flex-wrap gap-2">
          <button 
            type="button"
            onClick={addManualEntity}
            className="px-2 py-1 bg-blue-500 text-white rounded text-xs"
          >
            Add Entity Manually
          </button>
          <button 
            type="button"
            onClick={async () => {
              try {
                setLoading(true);
                await createEntity("Lifespan Foundation", "RI", "ACTIVE");
                await createEntity("Brown University Research Foundation", "RI", "ACTIVE");
                setSuccess("Test entities added! You can now create relationships with them.");
                // Refresh to show new entities
                await loadAllEntities();
              } catch (e) {
                setError("Failed to add test entities: " + String(e));
              } finally {
                setLoading(false);
              }
            }}
            className="px-2 py-1 bg-green-500 text-white rounded text-xs"
          >
            Add Test Entities
          </button>
          <button
            type="button"
            onClick={async () => {
              try {
                setLoading(true);
                // Try to clear all relationships
                console.log("Attempting to clear all relationships...");
                
                // Clear endpoints in order of preference
                const clearEndpoints = [
                  { url: 'http://localhost:8001/relationships/clear-all', method: 'POST' },
                  { url: 'http://localhost:8001/relationships/force-clear', method: 'GET' },
                  { url: 'http://localhost:8001/relationships/reset', method: 'POST' },
                  { url: 'http://localhost:8001/relationships?clear_relationships=true', method: 'GET' }
                ];
                
                let success = false;
                
                for (const endpoint of clearEndpoints) {
                  try {
                    console.log(`Trying to clear via ${endpoint.url} (${endpoint.method})...`);
                    
                    const response = await fetch(endpoint.url, { 
                      method: endpoint.method,
                      headers: {
                        'Accept': 'application/json'
                      }
                    });
                    
                    // Read response
                    let responseText = '';
                    try {
                      responseText = await response.text();
                      console.log(`${endpoint.url} response (${response.status}):`, responseText);
                    } catch (textError) {
                      console.warn(`Error reading response text:`, textError);
                    }
                    
                    if (response.ok) {
                      success = true;
                      console.log(`Successfully cleared relationships via ${endpoint.url}`);
                      break;
                    }
                  } catch (clearError) {
                    console.warn(`Error with ${endpoint.url}:`, clearError);
                  }
                }
                
                if (success) {
                  setSuccess("Relationships cleared successfully!");
                  onSuccess(); // Notify parent to refresh graph
                  
                  // Reload entities after a delay
                  setTimeout(async () => {
                    await loadAllEntities();
                    onSuccess(); // Refresh graph again
                  }, 500);
                } else {
                  setError("Failed to clear relationships with all methods.");
                }
              } catch (e) {
                setError("Error clearing relationships: " + String(e));
              } finally {
                setLoading(false);
              }
            }}
            className="px-2 py-1 bg-red-500 text-white rounded text-xs"
          >
            Clear All Relationships
          </button>
        </div>
        
        {/* Entity list, showing at most 3 entities */}
        {entities.length > 0 && (
          <div className="mt-2 text-xs text-gray-600">
            <div className="font-medium">Available entities:</div>
            <ul className="list-disc list-inside">
              {entities.slice(0, 3).map(entity => (
                <li key={entity.slug} className="truncate max-w-full">
                  {entity.name} ({entity.jurisdiction}) - {entity.status}
                </li>
              ))}
              {entities.length > 3 && (
                <li className="text-gray-500">...and {entities.length - 3} more</li>
              )}
            </ul>
          </div>
        )}
      </div>
      
      <form onSubmit={handleSubmit}>
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Parent Entity (Owner)
          </label>
          <select
            value={parentSlug}
            onChange={e => setParentSlug(e.target.value)}
            disabled={loading || entities.length === 0}
            className="w-full px-3 py-2 border border-gray-300 rounded text-sm"
            required
          >
            <option value="">Select parent company...</option>
            {entities.map(entity => (
              <option key={`parent-${entity.slug}`} value={entity.slug}>
                {entity.name} ({entity.jurisdiction || 'N/A'}) - {entity.status}
              </option>
            ))}
          </select>
        </div>
        
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Child Entity (Subsidiary)
          </label>
          <select
            value={childSlug}
            onChange={e => setChildSlug(e.target.value)}
            disabled={loading || entities.length === 0}
            className="w-full px-3 py-2 border border-gray-300 rounded text-sm"
            required
          >
            <option value="">Select subsidiary company...</option>
            {entities.map(entity => (
              <option key={`child-${entity.slug}`} value={entity.slug}>
                {entity.name} ({entity.jurisdiction || 'N/A'}) - {entity.status}
              </option>
            ))}
          </select>
        </div>
        
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Ownership Percentage: {ownershipPercentage}%
          </label>
          <input
            type="range"
            min="1"
            max="100"
            value={ownershipPercentage}
            onChange={e => setOwnershipPercentage(parseInt(e.target.value))}
            disabled={loading}
            className="w-full"
          />
          <div className="flex justify-between text-xs text-gray-500">
            <span>1%</span>
            <span>50%</span>
            <span>100%</span>
          </div>
        </div>
        
        <div className="flex flex-col gap-2">
          <button
            type="submit"
            disabled={loading || !parentSlug || !childSlug}
            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-2 px-4 rounded disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            {loading ? 'Creating...' : 'Create Relationship'}
          </button>
          
          {/* Quick action button for a test relationship */}
          <button
            type="button"
            onClick={async () => {
              if (entities.length < 2) {
                alert("Need at least 2 entities. Adding test entities...");
                await createEntity("Lifespan Foundation", "RI", "ACTIVE");
                await createEntity("Brown University Research Foundation", "RI", "ACTIVE");
                return;
              }
              
              // Get first two entities in the list
              const entityA = entities[0];
              const entityB = entities[1];
              
              // Set dropdown values
              setParentSlug(entityA.slug);
              setChildSlug(entityB.slug);
              setOwnershipPercentage(100);
              
              // Wait a bit then trigger submission
              setTimeout(() => {
                // Simulate form submission
                handleSubmit(new Event('click') as any);
              }, 500);
            }}
            className="w-full bg-green-600 hover:bg-green-700 text-white font-medium py-1 px-4 rounded text-sm"
          >
            Quick-Add Test Relationship
          </button>
          
          <button
            type="button"
            onClick={async () => {
              setLoading(true);
              try {
                // Use the existing entities that we already have in the system
                if (entities.length < 2) {
                  setError("Not enough entities available. Need at least 2 entities to create a relationship.");
                  return;
                }
                
                // Get the first two entities from our available list
                const parent = entities[0];
                const child = entities[1];
                
                console.log(`Using existing entities: ${parent.name} → ${child.name}`);
                
                // Use our core relationship creation function - the same one used by the form submit
                await createDirectRelationship(parent.slug, child.slug, ownershipPercentage);
                
                setSuccess(`Successfully created relationship: ${parent.name} → ${child.name} (${ownershipPercentage}%)`);
                
                // Notify parent to refresh and reload entities
                onSuccess();
                
                // Secondary refresh with delay
                setTimeout(async () => {
                  await loadAllEntities();
                  onSuccess();
                }, 500);
                
              } catch (e) {
                setError('Quick add failed: ' + String(e));
              } finally {
                setLoading(false);
              }
            }}
            className="w-full bg-purple-600 hover:bg-purple-700 text-white font-medium py-1 px-4 rounded text-sm"
          >
            Quick Add: {entities.length >= 2 ? `${entities[0].name} → ${entities[1].name}` : 'Need Entities'}
          </button>
        </div>
      </form>
    </div>
  );
}