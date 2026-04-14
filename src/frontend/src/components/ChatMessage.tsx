import { useState } from 'react';
import type { ChatMessage as ChatMessageType } from '../types';

interface ChatMessageProps {
  message: ChatMessageType;
}

function renderMarkdown(text: string): React.ReactNode {
  // Simple markdown: bold, inline code, code blocks, lists
  const lines = text.split('\n');
  const elements: React.ReactNode[] = [];
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i] ?? '';

    // Code block
    if (line.startsWith('```')) {
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !(lines[i] ?? '').startsWith('```')) {
        codeLines.push(lines[i] ?? '');
        i++;
      }
      // i now points at closing ``` (or past end); loop increment handles advance
      elements.push(
        <pre key={i} className="my-2 overflow-x-auto rounded bg-gray-800 p-3 text-sm text-gray-100">
          <code>{codeLines.join('\n')}</code>
        </pre>
      );
      continue;
    }

    // List items
    if (/^[-*]\s/.test(line)) {
      elements.push(
        <li key={i} className="ml-4 list-disc text-sm leading-relaxed">
          {formatInline(line.replace(/^[-*]\s/, ''))}
        </li>
      );
      continue;
    }

    // Numbered list
    if (/^\d+\.\s/.test(line)) {
      elements.push(
        <li key={i} className="ml-4 list-decimal text-sm leading-relaxed">
          {formatInline(line.replace(/^\d+\.\s/, ''))}
        </li>
      );
      continue;
    }

    // Regular paragraph
    if (line.trim()) {
      elements.push(
        <p key={i} className="text-sm leading-relaxed">
          {formatInline(line)}
        </p>
      );
    } else {
      elements.push(<br key={i} />);
    }
  }

  return elements;
}

function formatInline(text: string): React.ReactNode {
  // Handle bold (**text**) and inline code (`code`)
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  return parts.map((part, idx) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={idx}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith('`') && part.endsWith('`')) {
      return (
        <code key={idx} className="rounded bg-gray-100 px-1 py-0.5 text-xs text-pink-600">
          {part.slice(1, -1)}
        </code>
      );
    }
    return part;
  });
}

function CitationsAccordion({ citations }: { citations: ChatMessageType['citations'] }): React.ReactElement | null {
  const [expanded, setExpanded] = useState(false);

  if (!citations || citations.length === 0) return null;

  return (
    <div className="mt-2 border-t border-gray-300 pt-2">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700"
        aria-expanded={expanded}
      >
        <span>📄 {citations.length} source{citations.length > 1 ? 's' : ''}</span>
        <span className="text-[10px]">{expanded ? '▼' : '▶'}</span>
      </button>
      {expanded && (
        <ul className="mt-1 space-y-1">
          {citations.map((c, idx) => (
            <li key={idx} className="rounded bg-white/60 p-2 text-xs">
              <p className="font-medium text-gray-700">{c.title}</p>
              <p className="mt-0.5 text-gray-500 line-clamp-2">{c.content}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function TypingIndicator(): React.ReactElement {
  return (
    <span className="inline-flex gap-1" aria-label="Assistant is typing">
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-gray-400" style={{ animationDelay: '0ms' }} />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-gray-400" style={{ animationDelay: '150ms' }} />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-gray-400" style={{ animationDelay: '300ms' }} />
    </span>
  );
}

export default function ChatMessage({ message }: ChatMessageProps): React.ReactElement {
  const isUser = message.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div
        className={`max-w-[70%] rounded-2xl px-4 py-3 ${
          isUser
            ? 'bg-blue-600 text-white'
            : 'bg-gray-200 text-gray-900'
        }`}
      >
        {isUser ? (
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
        ) : message.isStreaming && !message.content ? (
          <TypingIndicator />
        ) : (
          <>
            <div className="whitespace-pre-wrap">{renderMarkdown(message.content)}</div>
            {message.isStreaming && <TypingIndicator />}
            <CitationsAccordion citations={message.citations} />
          </>
        )}
      </div>
    </div>
  );
}
