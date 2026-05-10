/**
 * ModelIndicator - Displays the current AI model name
 *
 * Shows a small pill in the bottom-right corner indicating
 * which model is powering the chat.
 */

interface ModelIndicatorProps {
  model?: string;
}

export function ModelIndicator({ model = 'AI Assistant' }: ModelIndicatorProps) {
  return (
    <div className="absolute bottom-4 right-4 flex items-center gap-2 px-3 py-2 bg-muted/50 backdrop-blur-sm rounded-full text-xs text-muted-foreground border border-border/50 z-10">
      <span>{model}</span>
    </div>
  );
}
