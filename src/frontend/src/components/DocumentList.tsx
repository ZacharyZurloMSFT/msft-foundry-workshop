import { useState } from 'react';
import type { Document } from '../types';

interface DocumentListProps {
  documents: Document[];
  loading: boolean;
  onDelete: (filename: string) => Promise<void>;
}

function fileIcon(filename: string): string {
  const ext = filename.slice(filename.lastIndexOf('.')).toLowerCase();
  if (ext === '.pdf') return '📄';
  if (ext === '.docx') return '📝';
  if (ext === '.txt') return '📃';
  return '📎';
}

export default function DocumentList({ documents, loading, onDelete }: DocumentListProps): React.ReactElement {
  const [deletingFile, setDeletingFile] = useState<string | null>(null);
  const [confirmFile, setConfirmFile] = useState<string | null>(null);

  const handleDelete = async (filename: string) => {
    setDeletingFile(filename);
    try {
      await onDelete(filename);
    } finally {
      setDeletingFile(null);
      setConfirmFile(null);
    }
  };

  if (loading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-14 animate-pulse rounded-md bg-gray-200" />
        ))}
      </div>
    );
  }

  if (documents.length === 0) {
    return (
      <div className="rounded-lg border-2 border-dashed border-gray-200 p-8 text-center">
        <p className="text-gray-500">No documents indexed yet. Upload your first document to get started.</p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">File</th>
            <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Chunks</th>
            <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Indexed</th>
            <th className="px-4 py-3 text-right text-xs font-medium uppercase text-gray-500">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {documents.map((doc) => (
            <tr key={doc.filename} className="hover:bg-gray-50">
              <td className="whitespace-nowrap px-4 py-3 text-sm">
                <span className="mr-2">{fileIcon(doc.filename)}</span>
                {doc.filename}
              </td>
              <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-600">{doc.chunk_count}</td>
              <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-600">
                {doc.indexed_date ? new Date(doc.indexed_date).toLocaleDateString() : '—'}
              </td>
              <td className="whitespace-nowrap px-4 py-3 text-right text-sm">
                {confirmFile === doc.filename ? (
                  <span className="space-x-2">
                    <span className="text-gray-500">Delete?</span>
                    <button
                      onClick={() => handleDelete(doc.filename)}
                      disabled={deletingFile === doc.filename}
                      className="font-medium text-red-600 hover:text-red-800 disabled:opacity-50"
                    >
                      {deletingFile === doc.filename ? 'Deleting…' : 'Yes'}
                    </button>
                    <button
                      onClick={() => setConfirmFile(null)}
                      className="font-medium text-gray-500 hover:text-gray-700"
                    >
                      No
                    </button>
                  </span>
                ) : (
                  <button
                    onClick={() => setConfirmFile(doc.filename)}
                    className="font-medium text-red-600 hover:text-red-800"
                  >
                    Delete
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
