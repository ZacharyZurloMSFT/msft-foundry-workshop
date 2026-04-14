import { useState } from 'react';
import ConversationSidebar from './components/ConversationSidebar';
import ChatPage from './pages/ChatPage';
import DocumentsPage from './pages/DocumentsPage';
import { useChat } from './hooks/useChat';

type Page = 'chat' | 'documents';

export default function App(): React.ReactElement {
  const [page, setPage] = useState<Page>('chat');
  const {
    messages,
    threadId,
    loading,
    error,
    conversations,
    sendMessage,
    loadConversation,
    newConversation,
    refreshConversations,
    deleteConversation,
  } = useChat();

  return (
    <div className="flex h-screen bg-gray-50">
      <ConversationSidebar
        conversations={conversations}
        activeThreadId={threadId}
        onSelect={(id) => { setPage('chat'); loadConversation(id); }}
        onNew={() => { setPage('chat'); newConversation(); }}
        onDelete={deleteConversation}
        onRefresh={refreshConversations}
      />

      <div className="flex flex-1 flex-col">
        <header className="flex h-14 items-center border-b border-gray-200 bg-white px-6 shadow-sm">
          <h1 className="text-lg font-bold text-gray-900">
            AI Foundry Workshop
          </h1>
          <nav className="ml-8 flex space-x-4">
            <button
              onClick={() => setPage('chat')}
              className={`text-sm font-medium ${page === 'chat' ? 'text-blue-600' : 'text-gray-500 hover:text-gray-700'}`}
            >
              Chat
            </button>
            <button
              onClick={() => setPage('documents')}
              className={`text-sm font-medium ${page === 'documents' ? 'text-blue-600' : 'text-gray-500 hover:text-gray-700'}`}
            >
              Documents
            </button>
          </nav>
        </header>
        <main className="flex-1 overflow-hidden">
          {page === 'chat' ? (
            <ChatPage
              messages={messages}
              loading={loading}
              error={error}
              onSend={sendMessage}
            />
          ) : (
            <DocumentsPage />
          )}
        </main>
      </div>
    </div>
  );
}
