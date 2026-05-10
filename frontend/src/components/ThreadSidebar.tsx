/**
 * ThreadSidebar - Collapsible sidebar for managing chat threads
 *
 * Features:
 * - List of conversation threads with timestamps
 * - Create, select, rename, and delete threads
 * - Collapsible with toggle button
 */

import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ChevronLeft, ChevronRight, Plus, Trash2, Edit2 } from 'lucide-react';
import { Thread } from '@/hooks/use-threads';
import { formatThreadTime } from '@/lib/datetime';
import { cn } from '@/lib/utils';
import { useState } from 'react';
import { Input } from '@/components/ui/input';
import { WarehousePanel } from '@/components/WarehousePanel';
import { WarehouseStatus } from '@/hooks/use-warehouse';

interface ThreadSidebarProps {
  threads: Thread[];
  currentThreadId: string | null;
  isOpen: boolean;
  onToggle: () => void;
  onSelectThread: (threadId: string) => void;
  onNewThread: () => void;
  onDeleteThread: (threadId: string) => void;
  onRenameThread: (threadId: string, newTitle: string) => void;
  onLogoClick: () => void;
  warehouseStatus: WarehouseStatus;
  onConfigureWarehouse: () => void;
  onDisconnectWarehouse: () => void;
}

export function ThreadSidebar({
  threads,
  currentThreadId,
  isOpen,
  onToggle,
  onSelectThread,
  onNewThread,
  onDeleteThread,
  onRenameThread,
  onLogoClick,
  warehouseStatus,
  onConfigureWarehouse,
  onDisconnectWarehouse,
}: ThreadSidebarProps) {
  const [editingThreadId, setEditingThreadId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState('');

  const handleStartEdit = (thread: Thread, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingThreadId(thread.id);
    setEditingTitle(thread.title);
  };

  const handleSaveEdit = (threadId: string) => {
    if (editingTitle.trim()) {
      onRenameThread(threadId, editingTitle.trim());
    }
    setEditingThreadId(null);
    setEditingTitle('');
  };

  const handleCancelEdit = () => {
    setEditingThreadId(null);
    setEditingTitle('');
  };

  return (
    <>
      {/* Sidebar */}
      <div
        className={cn(
          'fixed left-0 top-0 h-full bg-card border-r border-border transition-all duration-300 ease-in-out z-20',
          isOpen ? 'w-64' : 'w-0'
        )}
      >
        {isOpen && (
          <div className="flex flex-col h-full">
            {/* Logo */}
            <div className="p-4">
              <h1
                className="text-2xl font-bold tracking-tight cursor-pointer hover:opacity-70 transition-opacity"
                onClick={onLogoClick}
              >
                datachat
              </h1>
            </div>

            {/* Header */}
            <div className="p-3 flex items-center justify-between">
              <h2 className="font-semibold text-sm">Library</h2>
              <Button
                variant="ghost"
                size="icon"
                onClick={onNewThread}
                className="h-8 w-8"
              >
                <Plus className="h-4 w-4" />
              </Button>
            </div>

            {/* Thread List */}
            <ScrollArea className="flex-1">
              <div className="p-2 space-y-1">
                {threads.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground text-sm">
                    No conversations yet
                  </div>
                ) : (
                  threads.map((thread) => (
                    <div
                      key={thread.id}
                      className={cn(
                        'group relative p-2 rounded-lg cursor-pointer transition-colors',
                        currentThreadId === thread.id
                          ? 'bg-accent'
                          : 'hover:bg-accent/50'
                      )}
                      onClick={() => editingThreadId !== thread.id && onSelectThread(thread.id)}
                    >
                      {editingThreadId === thread.id ? (
                        <Input
                          value={editingTitle}
                          onChange={(e) => setEditingTitle(e.target.value)}
                          onBlur={() => handleSaveEdit(thread.id)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') {
                              handleSaveEdit(thread.id);
                            } else if (e.key === 'Escape') {
                              handleCancelEdit();
                            }
                          }}
                          className="h-6 text-sm"
                          autoFocus
                          onClick={(e) => e.stopPropagation()}
                        />
                      ) : (
                        <>
                          <p className="text-sm truncate pr-14">
                            {thread.title}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {formatThreadTime(thread.updatedAt)}
                          </p>
                        </>
                      )}
                      <div className="absolute right-2 top-1/2 -translate-y-1/2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity bg-inherit">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-6 w-6"
                          onClick={(e) => handleStartEdit(thread, e)}
                        >
                          <Edit2 className="h-3 w-3" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-6 w-6"
                          onClick={(e) => {
                            e.stopPropagation();
                            onDeleteThread(thread.id);
                          }}
                        >
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </ScrollArea>

            {/* Warehouse Panel */}
            <WarehousePanel
              warehouseStatus={warehouseStatus}
              onConfigure={onConfigureWarehouse}
              onDisconnect={onDisconnectWarehouse}
            />
          </div>
        )}
      </div>

      {/* Toggle Button */}
      <Button
        variant="ghost"
        size="icon"
        onClick={onToggle}
        className={cn(
          'fixed top-4 z-30 transition-all duration-300 rounded-full',
          isOpen ? 'left-64' : 'left-4'
        )}
      >
        {isOpen ? (
          <ChevronLeft className="h-5 w-5" />
        ) : (
          <ChevronRight className="h-5 w-5" />
        )}
      </Button>
    </>
  );
}
