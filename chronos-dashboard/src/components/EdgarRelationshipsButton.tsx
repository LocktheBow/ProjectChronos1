import { useState, useEffect } from 'react';
import { fetchRelationships } from '../hooks/useApi';

interface EdgarRelationshipsButtonProps {
  onRefresh: () => void;
}

export default function EdgarRelationshipsButton({ onRefresh }: EdgarRelationshipsButtonProps) {
  const [loading, setLoading] = useState(false);
  const [isExampleLoaded, setIsExampleLoaded] = useState(false);

  // Check for existing relationships on initial render and whenever refresh is triggered
  useEffect(() => {
    async function checkExistingRelationships() {
      try {
        const data = await fetchRelationships();
        // Only consider examples loaded if there are actual relationships
        const hasLinks = data.links && data.links.length > 0;
        console.log(`Relationship check: found ${data.links?.length || 0} links, setting isExampleLoaded=${hasLinks}`);
        setIsExampleLoaded(hasLinks);
      } catch (error) {
        console.error('Error checking relationship status:', error);
        setIsExampleLoaded(false);
      }
    }
    
    checkExistingRelationships();
  }, [onRefresh]); // Re-run whenever onRefresh reference changes (indicating a refresh occurred)

  const handleToggleRelationships = async () => {
    try {
      setLoading(true);
      
      if (isExampleLoaded) {
        // Clear relationships - try multiple API endpoints to ensure complete clearing
        console.log("Clearing relationships...");
        
        // Try the parameter-based method first
        await fetchRelationships(undefined, false, true);
        
        // Then try direct clear endpoints
        try {
          const clearResponse = await fetch('/relationships/clear');
          console.log("Direct clear endpoint response:", clearResponse.ok);
        } catch (e) {
          console.warn("Direct clear endpoint unavailable:", e);
        }
        
        try {
          const resetResponse = await fetch('/relationships/reset', { method: 'POST' });
          console.log("Reset endpoint response:", resetResponse.ok);
        } catch (e) {
          console.warn("Reset endpoint unavailable:", e);
        }
        
        console.log("Relationships cleared, refreshing graph...");
        setIsExampleLoaded(false);
      } else {
        // Load example relationships
        console.log("Loading example relationships...");
        await fetchRelationships(undefined, true);
        console.log("Example relationships loaded, refreshing graph...");
        setIsExampleLoaded(true);
      }
      
      // Tell the parent component to refresh the data
      onRefresh();
      
      // Ensure we refresh again after a short delay to catch any pending changes
      setTimeout(() => {
        onRefresh();
      }, 500);
    } catch (error) {
      console.error('Error toggling relationships:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      onClick={handleToggleRelationships}
      disabled={loading}
      className={`px-3 py-1 rounded text-sm transition-colors ${
        isExampleLoaded 
          ? 'bg-red-600 hover:bg-red-700 text-white' 
          : 'bg-indigo-600 hover:bg-indigo-700 text-white'
      }`}
    >
      {loading 
        ? 'Processing...' 
        : isExampleLoaded 
          ? 'Clear Example Relationships' 
          : 'Load Example Relationships'
      }
    </button>
  );
}