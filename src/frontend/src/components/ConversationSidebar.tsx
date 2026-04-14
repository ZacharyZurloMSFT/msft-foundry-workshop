import { useEffect, useState } from 'react';
import type { Conversation } from '../types';

interface ConversationSidebarProps {
  conversations: Conversation[];
  activeThreadId: string | null;
  onSelect: (threadId: string) => void;
  onNew: () => void;
  onDelete: (threadId: string) => void;
  onRefresh: () => void;
}

export default function ConversationSidebar({
  conversations,
  activeThreadId,
  onSelect,
  onNew,
  onDelete,
  onRefresh,
}: ConversationSidebarProps): React.ReactElement {
  const [collapsed, setCollapsed] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  useEffect(() => {
    onRefresh();
  }, [onRefresh]);

  if (collapsed) {
    return (
      <aside className="flex w-12 flex-shrink-0 flex-col items-center border-r border-gray-200 bg-white py-4">
        <button
          type="button"
          onClick={() => setCollapsed(false)}
          className="rounded p-1 text-gray-500 hover:bg-gray-100 hover:text-gray-700"
          aria-label="Expand sidebar"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </button>
      </aside>
    );
  }

  return (
    <aside className="flex w-64 flex-shrink-0 flex-col border-r border-gray-200 bg-white">
      <div className="flex items-center justify-between border-b border-gray-200 p-4">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-500">
          Conversations
        </h2>
        <button
          type="button"
          onClick={() => setCollapsed(true)}
          className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 md:hidden"
          aria-label="Collapse sidebar"
        >
          ✕
        </button>
      </div>

      <div className="p-3">
        <button
          type="button"
          onClick={onNew}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          + New Chat
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto px-2" aria-label="Conversation list">
        {conversations.length === 0 ? (
          <p className="px-2 py-4 text-center text-sm text-gray-400">No conversations yet</p>
        ) : (
          <ul className="space-y-1">
            {conversations.map((conv) => (
              <li key={conv.thread_id}>
                <div
                  className={`group flex items-center justify-between rounded-lg px-3 py-2 text-sm ${
                    activeThreadId === conv.thread_id
                      ? 'bg-blue-50 text-blue-700 font-medium'
                      : 'text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  <button
                    type="button"
                    onClick={() => onSelect(conv.thread_id)}
                    className="flex-1 truncate text-left"
                    title={conv.title}
                  >
                    {conv.title || 'Untitled'}
                  </button>
                  {confirmDelete === conv.thread_id ? (
                    <div className="flex gap-1">
                      <button
                        type="button"
                        onClick={() => { onDelete(conv.thread_id); setConfirmDelete(null); }}
                        className="text-xs text-red-600 hover:text-red-800"
                        aria-label="Confirm delete"
                      >
                        ✓
                      </button>
                      <button
                        type="button"
                        onClick={() => setConfirmDelete(null)}
                        className="text-xs text-gray-400 hover:text-gray-600"
                        aria-label="Cancel delete"
                      >
                        ✕
                      </button>
                    </div>
                  ) : (
                    <button
                      type="button"
                      onClick={() => setConfirmDelete(conv.thread_id)}
                      className="invisible text-xs text-gray-400 hover:text-red-500 group-hover:visible"
                      aria-label={`Delete conversation ${conv.title}`}
                    >
                      🗑
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </nav>
    </aside>
  );
}
