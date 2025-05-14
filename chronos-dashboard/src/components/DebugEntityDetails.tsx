import React from 'react';

interface DebugEntityDetailsProps {
  node: any;
  onClose: () => void;
}

/**
 * Debug component to show all properties of a node when clicked.
 * This is helpful for debugging and understanding what properties are available.
 */
export default function DebugEntityDetails({ node, onClose }: DebugEntityDetailsProps) {
  // Convert node to pretty JSON
  const nodeDetails = JSON.stringify(node, null, 2);
  
  return (
    <div className="fixed inset-0 bg-black/20 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white p-6 rounded-lg shadow-xl max-w-2xl max-h-[80vh] overflow-auto" onClick={e => e.stopPropagation()}>
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">Node Debug Details</h2>
          <button 
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xl"
          >
            ×
          </button>
        </div>
        <div className="border border-gray-200 rounded p-4 bg-gray-50">
          <pre className="text-xs text-gray-800 overflow-auto">{nodeDetails}</pre>
        </div>
        
        <div className="mt-4 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}