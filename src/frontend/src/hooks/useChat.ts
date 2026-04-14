import { useState, useCallback, useRef } from 'react';
import { API_BASE_URL } from '../config';
import { getMessages, getConversations } from '../api/client';
import type { ChatMessage, Citation, Conversation } from '../types';

interface UseChatReturn {
  messages: ChatMessage[];
  threadId: string | null;
  loading: boolean;
  error: string | null;
  conversations: Conversation[];
  sendMessage: (content: string) => Promise<void>;
  loadConversation: (threadId: string) => Promise<void>;
  newConversation: () => void;
  refreshConversations: () => Promise<void>;
  deleteConversation: (threadId: string) => Promise<void>;
}

export function useChat(): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const abortRef = useRef<AbortController | null>(null);

  const refreshConversations = useCallback(async (): Promise<void> => {
    try {
      const data = await getConversations();
      setConversations(data);
    } catch {
      // silently fail — sidebar is non-critical
    }
  }, []);

  const sendMessage = useCallback(async (content: string): Promise<void> => {
    setError(null);
    setLoading(true);

    const userMsg: ChatMessage = { role: 'user', content };
    setMessages(prev => [...prev, userMsg]);

    const assistantMsg: ChatMessage = { role: 'assistant', content: '', isStreaming: true };
    setMessages(prev => [...prev, assistantMsg]);

    try {
      abortRef.current = new AbortController();
      const res = await fetch(`${API_BASE_URL}/api/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: content,
          thread_id: threadId,
        }),
        signal: abortRef.current.signal,
      });

      if (!res.ok) {
        throw new Error(`Server error: ${res.status} ${res.statusText}`);
      }

      const reader = res.body?.getReader();
      if (!reader) throw new Error('No response stream available');

      const decoder = new TextDecoder();
      let accumulated = '';
      let citations: Citation[] = [];
      let newThreadId = threadId;
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') continue;

            try {
              const parsed = JSON.parse(data) as {
                delta?: string;
                thread_id?: string;
                citations?: Citation[];
                error?: string;
              };

              if (parsed.error) {
                throw new Error(parsed.error);
              }
              if (parsed.delta) {
                accumulated += parsed.delta;
                setMessages(prev => {
                  const updated = [...prev];
                  updated[updated.length - 1] = {
                    role: 'assistant',
                    content: accumulated,
                    citations,
                    isStreaming: true,
                  };
                  return updated;
                });
              }
              if (parsed.thread_id) {
                newThreadId = parsed.thread_id;
              }
              if (parsed.citations) {
                citations = parsed.citations;
              }
            } catch (e) {
              if (e instanceof SyntaxError) continue;
              throw e;
            }
          }
        }
      }

      // Finalize
      setMessages(prev => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: 'assistant',
          content: accumulated,
          citations,
          isStreaming: false,
        };
        return updated;
      });

      if (newThreadId) {
        setThreadId(newThreadId);
      }
      await refreshConversations();
    } catch (e) {
      if ((e as Error).name === 'AbortError') return;
      const message = e instanceof Error ? e.message : 'Something went wrong';
      setError(message);
      // Remove the empty assistant message on error
      setMessages(prev => prev.filter(m => !(m.role === 'assistant' && m.isStreaming && !m.content)));
    } finally {
      setLoading(false);
      abortRef.current = null;
    }
  }, [threadId, refreshConversations]);

  const loadConversation = useCallback(async (id: string): Promise<void> => {
    setError(null);
    setLoading(true);
    try {
      const data = await getMessages(id);
      setMessages(data);
      setThreadId(id);
    } catch {
      setError('Failed to load conversation');
    } finally {
      setLoading(false);
    }
  }, []);

  const newConversation = useCallback((): void => {
    setMessages([]);
    setThreadId(null);
    setError(null);
  }, []);

  const deleteConversation = useCallback(async (id: string): Promise<void> => {
    try {
      await fetch(`${API_BASE_URL}/api/conversations/${id}`, { method: 'DELETE' });
      if (threadId === id) {
        newConversation();
      }
      await refreshConversations();
    } catch {
      setError('Failed to delete conversation');
    }
  }, [threadId, newConversation, refreshConversations]);

  return {
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
  };
}
