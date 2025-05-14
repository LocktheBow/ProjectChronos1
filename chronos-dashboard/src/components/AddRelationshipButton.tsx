import { useState } from 'react';
import AddRelationshipForm from './AddRelationshipForm';

interface AddRelationshipButtonProps {
  onRefresh: () => void;
}

export default function AddRelationshipButton({ onRefresh }: AddRelationshipButtonProps) {
  const [showForm, setShowForm] = useState(false);
  
  const toggleForm = () => {
    setShowForm(prev => !prev);
  };
  
  const handleSuccess = () => {
    // Refresh the graph data when a relationship is successfully added
    onRefresh();
  };
  
  return (
    <div className="relative">
      <button
        className="px-3 py-1 bg-white border border-gray-300 rounded text-sm hover:bg-[#F9FAFB]"
        onClick={toggleForm}
      >
        {showForm ? 'Hide Form' : 'Add Relationship'}
      </button>
      
      {showForm && (
        <div className="absolute right-0 top-10 z-10 w-96 shadow-lg bg-white rounded-lg">
          <AddRelationshipForm onSuccess={handleSuccess} />
        </div>
      )}
    </div>
  );
}