import { API_BASE_URL } from '../config';
import type { ChatResponse, ChatMessage, Document, Conversation } from '../types';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}/api${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export async function sendMessage(
  message: string,
  threadId?: string,
): Promise<ChatResponse> {
  return request<ChatResponse>('/chat', {
    method: 'POST',
    body: JSON.stringify({ message, thread_id: threadId }),
  });
}

export async function getMessages(threadId: string): Promise<ChatMessage[]> {
  return request<ChatMessage[]>(`/chat/${threadId}/messages`);
}

export async function uploadDocument(file: File): Promise<Document> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${API_BASE_URL}/api/documents`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<Document>;
}

export async function getDocuments(): Promise<Document[]> {
  return request<Document[]>('/documents');
}

export async function deleteDocument(filename: string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/documents/${encodeURIComponent(filename)}`, {
    method: 'DELETE',
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
}

export async function getConversations(): Promise<Conversation[]> {
  return request<Conversation[]>('/conversations');
}

export async function seedDocuments(force = false): Promise<{ total_seeded: number; seeded: string[]; skipped: string[]; errors: string[] }> {
  return request('/documents/seed' + (force ? '?force=true' : ''), { method: 'POST' });
}
