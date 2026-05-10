/**
 * useThreads - Chat thread state management
 *
 * Manages multiple conversation threads with localStorage persistence.
 * Provides CRUD operations: create, delete, update, switch, rename.
 * Auto-generates thread titles from first user message.
 */

import { useState, useEffect } from 'react';

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  query?: any;
  sql?: string;
  showQuery?: boolean;
}

export interface Thread {
  id: string;
  title: string;
  createdAt: Date;
  updatedAt: Date;
  messages: Message[];
  sessionId?: string; // Backend session ID for conversation context
}

const STORAGE_KEY = 'retailflow-threads';

export function useThreads() {
  const [threads, setThreads] = useState<Thread[]>(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        return parsed.map((thread: any) => ({
          ...thread,
          createdAt: new Date(thread.createdAt),
          updatedAt: new Date(thread.updatedAt),
        }));
      } catch (e) {
        return [];
      }
    }
    return [];
  });

  // Start with no thread selected to show welcome screen on new sessions
  const [currentThreadId, setCurrentThreadId] = useState<string | null>(null);

  useEffect(() => {
    const toStore = threads.map(thread => ({
      ...thread,
      createdAt: thread.createdAt.toISOString(),
      updatedAt: thread.updatedAt.toISOString(),
    }));
    localStorage.setItem(STORAGE_KEY, JSON.stringify(toStore));
  }, [threads]);

  const currentThread = threads.find(t => t.id === currentThreadId) || null;

  const createThread = () => {
    const newThread: Thread = {
      id: Date.now().toString(),
      title: 'New Chat',
      createdAt: new Date(),
      updatedAt: new Date(),
      messages: [],
    };
    setThreads(prev => [newThread, ...prev]);
    setCurrentThreadId(newThread.id);
    return newThread;
  };

  const deleteThread = (threadId: string) => {
    setThreads(prev => {
      const filtered = prev.filter(t => t.id !== threadId);
      if (currentThreadId === threadId && filtered.length > 0) {
        setCurrentThreadId(filtered[0].id);
      } else if (filtered.length === 0) {
        setCurrentThreadId(null);
      }
      return filtered;
    });
  };

  const updateThread = (threadId: string, messages: Message[]) => {
    setThreads(prev => prev.map(thread => {
      if (thread.id === threadId) {
        // Generate title from first user message if still "New Chat"
        let title = thread.title;
        if (thread.title === 'New Chat' && messages.length > 0) {
          const content = messages[0].content.trim();
          const maxLength = 28;
          if (content.length <= maxLength) {
            title = content;
          } else {
            // Break at word boundary
            const truncated = content.slice(0, maxLength);
            const lastSpace = truncated.lastIndexOf(' ');
            title = (lastSpace > 10 ? truncated.slice(0, lastSpace) : truncated) + '...';
          }
        }

        return {
          ...thread,
          messages,
          title,
          updatedAt: new Date(),
        };
      }
      return thread;
    }));
  };

  const switchThread = (threadId: string) => {
    setCurrentThreadId(threadId);
  };

  const clearCurrentThread = () => {
    setCurrentThreadId(null);
  };

  const renameThread = (threadId: string, newTitle: string) => {
    setThreads(prev => prev.map(thread => {
      if (thread.id === threadId) {
        return {
          ...thread,
          title: newTitle,
          updatedAt: new Date(),
        };
      }
      return thread;
    }));
  };

  const setThreadSessionId = (threadId: string, sessionId: string) => {
    setThreads(prev => prev.map(thread => {
      if (thread.id === threadId) {
        return { ...thread, sessionId };
      }
      return thread;
    }));
  };

  return {
    threads,
    currentThread,
    currentThreadId,
    createThread,
    deleteThread,
    updateThread,
    switchThread,
    clearCurrentThread,
    renameThread,
    setThreadSessionId,
  };
}
