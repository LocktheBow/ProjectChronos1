import { useState, useEffect } from 'react';
import { api, searchEntities } from '../hooks/useApi';

interface AddRelationshipFormProps {
  onSuccess: () => void;
}

interface Entity {
  slug: string;
  name: string;
}

export default function AddRelationshipForm({ onSuccess }: AddRelationshipFormProps) {
  const [entities, setEntities] = useState<Entity[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  // Form state
  const [parentSlug, setParentSlug] = useState('');
  const [childSlug, setChildSlug] = useState('');
  const [ownershipPercentage, setOwnershipPercentage] = useState(100);
  
  // Load entities for select dropdowns
  useEffect(() => {
    async function loadEntities() {
      try {
        setLoading(true);
        // Fetch a list of entities using the search entities function 
        // with an empty query to get all entities
        const response = await searchEntities('', undefined);
        setEntities(response);
      } catch (err) {
        console.error('Error loading entities:', err);
        setError('Failed to load entities. Please refresh and try again.');
      } finally {
        setLoading(false);
      }
    }
    
    loadEntities();
  }, []);
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validation
    if (!parentSlug || !childSlug) {
      setError('Please select both parent and child entities');
      return;
    }
    
    if (parentSlug === childSlug) {
      setError('Parent and child cannot be the same entity');
      return;
    }
    
    if (ownershipPercentage < 0 || ownershipPercentage > 100) {
      setError('Ownership percentage must be between 0 and 100');
      return;
    }
    
    try {
      setLoading(true);
      setError(null);
      setSuccess(null);
      
      // Create the relationship
      const response = await api('/relationships', {
        method: 'POST',
        body: JSON.stringify({
          parent_slug: parentSlug,
          child_slug: childSlug,
          ownership_percentage: ownershipPercentage
        })
      });
      
      // Show success message
      setSuccess(`Successfully created relationship: ${response.message}`);
      
      // Reset form
      setParentSlug('');
      setChildSlug('');
      setOwnershipPercentage(100);
      
      // Notify parent component
      onSuccess();
      
    } catch (err) {
      console.error('Error creating relationship:', err);
      setError('Failed to create relationship. ' + (err instanceof Error ? err.message : String(err)));
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="bg-white shadow rounded-lg p-6 mb-6">
      <h2 className="text-lg font-semibold mb-4">Add Relationship</h2>
      
      {/* Success Message */}
      {success && (
        <div className="mb-4 p-2 bg-green-100 border border-green-300 text-green-800 rounded">
          {success}
        </div>
      )}
      
      {/* Error Message */}
      {error && (
        <div className="mb-4 p-2 bg-red-100 border border-red-300 text-red-800 rounded">
          {error}
        </div>
      )}
      
      <form onSubmit={handleSubmit}>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {/* Parent Entity Dropdown */}
          <div>
            <label htmlFor="parentEntity" className="block text-sm font-medium text-gray-700 mb-1">
              Parent Entity (Owner)
            </label>
            <select
              id="parentEntity"
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              value={parentSlug}
              onChange={(e) => setParentSlug(e.target.value)}
              disabled={loading || entities.length === 0}
              required
            >
              <option value="">Select a parent entity...</option>
              {entities.map((entity) => (
                <option key={`parent-${entity.slug}`} value={entity.slug}>
                  {entity.name}
                </option>
              ))}
            </select>
          </div>
          
          {/* Child Entity Dropdown */}
          <div>
            <label htmlFor="childEntity" className="block text-sm font-medium text-gray-700 mb-1">
              Child Entity (Subsidiary)
            </label>
            <select
              id="childEntity"
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              value={childSlug}
              onChange={(e) => setChildSlug(e.target.value)}
              disabled={loading || entities.length === 0}
              required
            >
              <option value="">Select a child entity...</option>
              {entities.map((entity) => (
                <option key={`child-${entity.slug}`} value={entity.slug}>
                  {entity.name}
                </option>
              ))}
            </select>
          </div>
        </div>
        
        {/* Ownership Percentage Slider */}
        <div className="mt-4">
          <label htmlFor="ownershipPercentage" className="block text-sm font-medium text-gray-700 mb-1">
            Ownership Percentage: {ownershipPercentage}%
          </label>
          <input
            id="ownershipPercentage"
            type="range"
            min="0"
            max="100"
            step="1"
            className="w-full"
            value={ownershipPercentage}
            onChange={(e) => setOwnershipPercentage(parseInt(e.target.value))}
            disabled={loading}
          />
        </div>
        
        {/* Submit Button */}
        <div className="mt-6">
          <button
            type="submit"
            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-2 px-4 rounded-md disabled:bg-gray-400"
            disabled={loading || !parentSlug || !childSlug}
          >
            {loading ? 'Creating...' : 'Create Relationship'}
          </button>
        </div>
      </form>
    </div>
  );
}