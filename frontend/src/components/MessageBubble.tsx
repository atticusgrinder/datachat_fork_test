/**
 * MessageBubble - Renders a single chat message
 *
 * Displays user and assistant messages with distinct styling.
 * For assistant messages, optionally shows expandable query details
 * (semantic query JSON and generated SQL).
 */

import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Message } from '@/hooks/use-threads';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface MessageBubbleProps {
  message: Message;
  onToggleQuery: (messageId: string) => void;
}

// Preprocess markdown to ensure lists are properly formatted
// Adds blank line before numbered/bulleted lists if missing
const normalizeMarkdown = (content: string): string => {
  return content
    // Add blank line before numbered lists (1. 2. etc) if not already present
    .replace(/([^\n])\n(\d+\.\s)/g, '$1\n\n$2')
    // Add blank line before bulleted lists (- or *) if not already present
    .replace(/([^\n])\n([-*]\s)/g, '$1\n\n$2');
};

export const MessageBubble = ({ message, onToggleQuery }: MessageBubbleProps) => {
  return (
    <div
      className={`flex ${
        message.role === 'user' ? 'justify-end' : 'justify-start'
      }`}
    >
      <div className="max-w-[80%] space-y-2">
        <div
          className={`${
            message.role === 'user'
              ? 'px-4 py-2.5 bg-[hsl(var(--user-message))] text-[hsl(var(--user-message-foreground))] rounded-2xl'
              : 'px-4 py-3 bg-[hsl(var(--ai-message))] text-[hsl(var(--ai-message-foreground))] rounded-2xl'
          }`}
        >
          {message.role === 'user' ? (
            <p className="text-sm whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="text-sm prose prose-sm dark:prose-invert prose-p:my-3 prose-ul:my-3 prose-ol:my-3 prose-li:my-0.5 prose-headings:my-4 max-w-none [&>*:first-child]:mt-0 [&>*]:block [&_strong]:block [&_p:has(strong:only-child)]:mb-1 [&_p:has(strong:only-child)+ol]:mt-0 [&_p:has(strong:only-child)+ul]:mt-0">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {normalizeMarkdown(message.content)}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {message.role === 'assistant' && (message.query || message.sql) && (
          <>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onToggleQuery(message.id)}
              className="text-xs"
            >
              {message.showQuery ? 'Hide' : 'Show'} Query Details
            </Button>

            {message.showQuery && (
              <div className="space-y-2">
                {message.query && (
                  <Card className="p-3 bg-muted">
                    <p className="text-xs font-semibold mb-2">Semantic Query:</p>
                    <pre className="text-xs overflow-x-auto">
                      {JSON.stringify(message.query, null, 2)}
                    </pre>
                  </Card>
                )}

                {message.sql && (
                  <Card className="p-3 bg-muted">
                    <p className="text-xs font-semibold mb-2">SQL Query:</p>
                    <pre className="text-xs overflow-x-auto whitespace-pre-wrap">
                      {message.sql}
                    </pre>
                  </Card>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};
