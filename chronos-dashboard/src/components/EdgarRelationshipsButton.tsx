import { useState } from 'react';
import { fetchRelationships } from '../hooks/useApi';

interface EdgarRelationshipsButtonProps {
  onRefresh: () => void;
}

export default function EdgarRelationshipsButton({ onRefresh }: EdgarRelationshipsButtonProps) {
  const [loading, setLoading] = useState(false);

  const handleLoadExampleRelationships = async () => {
    try {
      setLoading(true);
      console.log("Loading example relationships...");
      // This will trigger the loading of example relationships on the backend
      await fetchRelationships(undefined, true);
      console.log("Example relationships loaded, refreshing graph...");
      // Tell the parent component to refresh the data
      onRefresh();
    } catch (error) {
      console.error('Error loading example relationships:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      onClick={handleLoadExampleRelationships}
      disabled={loading}
      className="px-3 py-1 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700 transition-colors"
    >
      {loading ? 'Loading...' : 'Load Example Relationships'}
    </button>
  );
}