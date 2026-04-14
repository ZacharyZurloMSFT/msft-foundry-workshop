import { useEffect, useRef } from 'react';
import ChatMessage from '../components/ChatMessage';
import ChatInput from '../components/ChatInput';
import type { ChatMessage as ChatMessageType } from '../types';

interface ChatPageProps {
  messages: ChatMessageType[];
  loading: boolean;
  error: string | null;
  onSend: (content: string) => void;
}

export default function ChatPage({ messages, loading, error, onSend }: ChatPageProps): React.ReactElement {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto p-6">
        {messages.length === 0 ? (
          <div className="flex h-full items-center justify-center">
            <p className="text-gray-400">Start a conversation by typing a message below</p>
          </div>
        ) : (
          <>
            {messages.map((msg, i) => (
              <ChatMessage key={i} message={msg} />
            ))}
            <div ref={bottomRef} />
          </>
        )}
      </div>

      {error && (
        <div className="mx-4 mb-2 rounded-lg bg-red-50 px-4 py-2 text-sm text-red-600" role="alert">
          {error}
        </div>
      )}

      <ChatInput onSend={onSend} disabled={loading} />
    </div>
  );
}
