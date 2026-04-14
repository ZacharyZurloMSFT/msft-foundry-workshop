import { useState, useEffect, useCallback } from 'react';
import FileUpload from '../components/FileUpload';
import DocumentList from '../components/DocumentList';
import { uploadDocument, getDocuments, deleteDocument } from '../api/client';
import type { Document } from '../types';

export default function DocumentsPage(): React.ReactElement {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
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

      <FileUpload onUpload={handleUpload} uploading={uploading} />

      <DocumentList documents={documents} loading={loading} onDelete={handleDelete} />
    </div>
  );
}
