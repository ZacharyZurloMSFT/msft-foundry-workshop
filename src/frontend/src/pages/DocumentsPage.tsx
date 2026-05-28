import { useState, useEffect, useCallback } from 'react';
import FileUpload from '../components/FileUpload';
import DocumentList from '../components/DocumentList';
import { uploadDocument, getDocuments, deleteDocument, seedDocuments } from '../api/client';
import type { Document } from '../types';

export default function DocumentsPage(): React.ReactElement {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  const showToast = (message: string, type: 'success' | 'error') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  const fetchDocuments = useCallback(async () => {
    try {
      const docs = await getDocuments();
      setDocuments(docs);
    } catch {
      showToast('Failed to load documents.', 'error');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchDocuments();
  }, [fetchDocuments]);

  const handleUpload = async (file: File) => {
    setUploading(true);
    try {
      await uploadDocument(file);
      showToast(`"${file.name}" uploaded successfully!`, 'success');
      await fetchDocuments();
    } catch {
      showToast(`Failed to upload "${file.name}".`, 'error');
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (filename: string) => {
    try {
      await deleteDocument(filename);
      showToast(`"${filename}" deleted.`, 'success');
      await fetchDocuments();
    } catch {
      showToast(`Failed to delete "${filename}".`, 'error');
    }
  };

  const handleSeedSamples = async () => {
    setSeeding(true);
    try {
      const result = await seedDocuments();
      if (result.total_seeded > 0) {
        showToast(`Loaded ${result.total_seeded} sample document(s) successfully!`, 'success');
      } else if (result.skipped.length > 0) {
        showToast('Sample documents are already loaded.', 'success');
      } else {
        showToast('No sample documents were loaded.', 'error');
      }
      await fetchDocuments();
    } catch {
      showToast('Failed to load sample documents.', 'error');
    } finally {
      setSeeding(false);
    }
  };

  return (
    <div className="mx-auto max-w-4xl space-y-8 p-6">
      {/* Toast */}
      {toast && (
        <div
          className={`fixed right-6 top-20 z-50 rounded-md px-4 py-3 text-sm font-medium shadow-lg transition-all ${
            toast.type === 'success'
              ? 'bg-green-50 text-green-800 border border-green-200'
              : 'bg-red-50 text-red-800 border border-red-200'
          }`}
        >
          {toast.message}
        </div>
      )}

      <div>
        <h2 className="text-xl font-bold text-gray-900">Documents</h2>
        <p className="mt-1 text-sm text-gray-500">Upload and manage your indexed documents.</p>
      </div>

      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500">
          {documents.length} document{documents.length !== 1 ? 's' : ''} indexed
        </p>
        <button
          onClick={() => void handleSeedSamples()}
          disabled={seeding}
          className="inline-flex items-center gap-2 rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {seeding ? (
            <>
              <svg className="h-4 w-4 animate-spin text-gray-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              Loading samples…
            </>
          ) : (
            <>
              <svg className="h-4 w-4 text-gray-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
              </svg>
              Load Sample Documents
            </>
          )}
        </button>
      </div>

      <FileUpload onUpload={handleUpload} uploading={uploading} />

      <DocumentList documents={documents} loading={loading} onDelete={handleDelete} />
    </div>
  );
}
