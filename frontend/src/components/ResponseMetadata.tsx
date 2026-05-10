import { useState, memo } from "react";
import { api } from "@/lib/api";
import { Clock, Coins, ThumbsUp, ThumbsDown } from "lucide-react";

interface ResponseMetadataProps {
  messageId: string;
  createdAt: string;
  durationMs?: number;
  inputTokens?: number;
  outputTokens?: number;
  feedback?: "like" | "dislike" | null;
  onFeedbackChange?: (feedback: "like" | "dislike" | null) => void;
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function formatTokens(count: number): string {
  if (count >= 1000) return `${(count / 1000).toFixed(1)}k`;
  return `${count}`;
}

export function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  const now = new Date();
  const isToday =
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate();

  const time = date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });

  if (isToday) return time;

  const mm = String(date.getMonth() + 1).padStart(2, "0");
  const dd = String(date.getDate()).padStart(2, "0");
  const yy = String(date.getFullYear()).slice(-2);
  return `${mm}/${dd}/${yy} ${time}`;
}

export default memo(function ResponseMetadata({
  messageId,
  createdAt,
  durationMs,
  inputTokens,
  outputTokens,
  feedback: initialFeedback,
  onFeedbackChange,
}: ResponseMetadataProps) {
  const [feedback, setFeedback] = useState<"like" | "dislike" | null>(initialFeedback ?? null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const totalTokens = (inputTokens || 0) + (outputTokens || 0);

  const handleFeedback = async (rating: "like" | "dislike") => {
    if (isSubmitting) return;
    setIsSubmitting(true);

    try {
      if (feedback === rating) {
        await api.removeFeedback(messageId);
        setFeedback(null);
        onFeedbackChange?.(null);
      } else {
        await api.submitFeedback(messageId, rating);
        setFeedback(rating);
        onFeedbackChange?.(rating);
      }
    } catch {
      // Silently fail - feedback is non-critical
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="mt-1 flex items-center gap-3 text-xs text-muted-foreground">
      <span>{formatTimestamp(createdAt)}</span>
      {durationMs != null && durationMs > 0 && (
        <span className="flex items-center gap-1">
          <Clock className="h-3 w-3" />
          {formatDuration(durationMs)}
        </span>
      )}
      {totalTokens > 0 && (
        <span className="flex items-center gap-1">
          <Coins className="h-3 w-3" />
          {formatTokens(totalTokens)} tokens
        </span>
      )}
      <span className="flex items-center gap-1">
        <button
          onClick={() => handleFeedback("like")}
          disabled={isSubmitting}
          className={`p-0.5 rounded transition-colors ${
            feedback === "like"
              ? "text-green-500"
              : "hover:text-foreground"
          }`}
          title="Like"
        >
          <ThumbsUp className="h-3 w-3" />
        </button>
        <button
          onClick={() => handleFeedback("dislike")}
          disabled={isSubmitting}
          className={`p-0.5 rounded transition-colors ${
            feedback === "dislike"
              ? "text-red-500"
              : "hover:text-foreground"
          }`}
          title="Dislike"
        >
          <ThumbsDown className="h-3 w-3" />
        </button>
      </span>
    </div>
  );
});
