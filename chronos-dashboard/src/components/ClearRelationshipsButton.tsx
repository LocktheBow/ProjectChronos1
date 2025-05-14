import { useState } from 'react';
import { api } from '../hooks/useApi';

interface ClearRelationshipsButtonProps {
  onRefresh: () => void;
}

export default function ClearRelationshipsButton({ onRefresh }: ClearRelationshipsButtonProps) {
  const [loading, setLoading] = useState(false);

  const handleClearRelationships = async () => {
    if (!confirm('Are you sure you want to clear all relationships from the graph?')) {
      return;
    }
    
    try {
      setLoading(true);
      console.log("Clearing all relationships - will try multiple methods for completeness");
      
      // First, store a list of all methods and their priority
      const clearMethods = [
        {
          name: "POST /relationships/clear-all endpoint",
          fn: async () => {
            const response = await fetch('/relationships/clear-all', { 
              method: 'POST',
              headers: { 'Content-Type': 'application/json' } 
            });
            return response.ok;
          }
        },
        {
          name: "GET /relationships/force-clear endpoint",
          fn: async () => {
            const response = await fetch('/relationships/force-clear');
            return response.ok;
          }
        },
        {
          name: "GET /relationships/empty endpoint",
          fn: async () => {
            const response = await fetch('/relationships/empty');
            return response.ok;
          }
        },
        {
          name: "GET /relationships?clear_relationships=true parameter",
          fn: async () => {
            const response = await fetch('/relationships?clear_relationships=true');
            return response.ok;
          }
        },
        {
          name: "POST /relationships/reset endpoint",
          fn: async () => {
            const response = await fetch('/relationships/reset', { method: 'POST' });
            return response.ok;
          }
        }
      ];
      
      // Try all methods one by one, tracking which ones succeed
      let successfulMethods = 0;
      for (const method of clearMethods) {
        try {
          console.log(`Trying ${method.name}...`);
          const success = await method.fn();
          if (success) {
            console.log(`✓ ${method.name} succeeded`);
            successfulMethods++;
          } else {
            console.log(`✗ ${method.name} failed with non-OK response`);
          }
        } catch (e) {
          console.warn(`✗ ${method.name} failed with error:`, e);
          // Continue to next method
        }
      }
      
      console.log(`Completed ${successfulMethods} of ${clearMethods.length} clear methods`);
      
      // Always refresh the UI data regardless of success/failure count
      onRefresh();
      
      // Double refresh with a small delay to ensure the UI updates completely
      setTimeout(() => {
        console.log("Secondary refresh to ensure UI updates...");
        onRefresh();
      }, 1000);
    } catch (error) {
      console.error('Error in main clear relationships process:', error);
      alert('Failed to clear all relationships. Please try refreshing the page.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      onClick={handleClearRelationships}
      disabled={loading}
      className="px-3 py-1 bg-red-600 text-white rounded text-sm hover:bg-red-700 transition-colors ml-2"
    >
      {loading ? 'Clearing...' : 'Clear Relationships'}
    </button>
  );
}