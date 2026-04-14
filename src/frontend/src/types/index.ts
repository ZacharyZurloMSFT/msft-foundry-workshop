export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  isStreaming?: boolean;
}

export interface Citation {
  title: string;
  url: string;
  content: string;
}

export interface ChatResponse {
  response: string;
  thread_id: string;
  citations: Citation[];
}

export interface Document {
  filename: string;
  chunk_count: number;
  indexed_date?: string;
}

export interface Conversation {
  thread_id: string;
  title: string;
  created_at: string;
}

export interface SSEEvent {
  event?: string;
  data: string;
}
