import { useState, useRef, useCallback } from 'react';

const ACCEPTED_TYPES = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'text/plain',
];
const ACCEPTED_EXTENSIONS = ['.pdf', '.docx', '.txt'];
const MAX_SIZE_BYTES = 10 * 1024 * 1024; // 10MB

interface FileUploadProps {
  onUpload: (file: File) => Promise<void>;
  uploading: boolean;
}

export default function FileUpload({ onUpload, uploading }: FileUploadProps): React.ReactElement {
  const [dragOver, setDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const validate = useCallback((file: File): string | null => {
    const ext = file.name.slice(file.name.lastIndexOf('.')).toLowerCase();
    if (!ACCEPTED_EXTENSIONS.includes(ext) && !ACCEPTED_TYPES.includes(file.type)) {
      return 'Only PDF, DOCX, and TXT files are accepted.';
    }
    if (file.size > MAX_SIZE_BYTES) {
      return 'File size must be under 10 MB.';
    }
    return null;
  }, []);

  const handleFile = useCallback((file: File) => {
    const error = validate(file);
    setValidationError(error);
    if (!error) {
      setSelectedFile(file);
    } else {
      setSelectedFile(null);
    }
  }, [validate]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, [handleFile]);

  const handleUploadClick = async () => {
    if (!selectedFile) return;
    await onUpload(selectedFile);
    setSelectedFile(null);
    if (inputRef.current) inputRef.current.value = '';
  };

  return (
    <div className="space-y-3">
      <div
        role="button"
        tabIndex={0}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click(); }}
        className={`flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 text-center transition-colors cursor-pointer ${
          dragOver
            ? 'border-blue-500 bg-blue-50'
            : 'border-gray-300 bg-white hover:border-gray-400'
        }`}
      >
        <svg className="mx-auto h-10 w-10 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 16V4m0 0l-4 4m4-4 4 4M4 14v4a2 2 0 002 2h12a2 2 0 002-2v-4" />
        </svg>
        <p className="mt-2 text-sm text-gray-600">
          Drag & drop a file here, or <span className="font-medium text-blue-600">click to browse</span>
        </p>
        <p className="mt-1 text-xs text-gray-400">PDF, DOCX, TXT — max 10 MB</p>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx,.txt"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFile(file);
          }}
        />
      </div>

      {validationError && (
        <p className="text-sm text-red-600">{validationError}</p>
      )}

      {selectedFile && !validationError && (
        <div className="flex items-center justify-between rounded-md bg-gray-50 px-4 py-2">
          <span className="truncate text-sm text-gray-700">{selectedFile.name}</span>
          <button
            onClick={handleUploadClick}
            disabled={uploading}
            className="ml-4 inline-flex items-center rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {uploading ? (
              <>
                <svg className="mr-2 h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
                </svg>
                Uploading…
              </>
            ) : (
              'Upload'
            )}
          </button>
        </div>
      )}
    </div>
  );
}
