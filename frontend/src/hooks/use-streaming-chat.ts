import { useState, useRef, useCallback } from "react";
import { api, StreamDoneData } from "@/lib/api";

export interface ToolCallInfo {
  tool_name: string;
  tool_input?: Record<string, any>;
  status: "running" | "completed" | "error";
}

interface UseStreamingChatReturn {
  isStreaming: boolean;
  streamingText: string;
  statusMessage: string;
  toolCalls: ToolCallInfo[];
  doneData: StreamDoneData | null;
  error: string | null;
  sendMessage: (params: {
    message: string;
    conversation_id?: string;
    warehouse_id?: string;
    salesforce_id?: string;
    file_session_id?: string;
    local_duckdb_id?: string;
    model?: string;
  }) => Promise<void>;
  cancel: () => void;
  reset: () => void;
}

export function useStreamingChat(): UseStreamingChatReturn {
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [statusMessage, setStatusMessage] = useState("");
  const [toolCalls, setToolCalls] = useState<ToolCallInfo[]>([]);
  const [doneData, setDoneData] = useState<StreamDoneData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const reset = useCallback(() => {
    setIsStreaming(false);
    setStreamingText("");
    setStatusMessage("");
    setToolCalls([]);
    setDoneData(null);
    setError(null);
  }, []);

  const cancel = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsStreaming(false);
  }, []);

  const sendMessage = useCallback(async (params: {
    message: string;
    conversation_id?: string;
    warehouse_id?: string;
    salesforce_id?: string;
    file_session_id?: string;
    local_duckdb_id?: string;
    model?: string;
  }) => {
    // Reset state for new message
    setIsStreaming(true);
    setStreamingText("");
    setStatusMessage("");
    setToolCalls([]);
    setDoneData(null);
    setError(null);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const response = await api.sendMessageStream({
        ...params,
        signal: controller.signal,
      });

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error("No response body");
      }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Parse SSE events from buffer
        const lines = buffer.split("\n");
        buffer = lines.pop() || ""; // Keep incomplete line in buffer

        let currentEvent = "";
        for (const line of lines) {
          if (line.startsWith("event: ")) {
            currentEvent = line.slice(7);
          } else if (line.startsWith("data: ") && currentEvent) {
            try {
              const data = JSON.parse(line.slice(6));
              switch (currentEvent) {
                case "status":
                  setStatusMessage(data.message);
                  break;
                case "text_delta":
                  setStreamingText((prev) => prev + data.delta);
                  setStatusMessage(""); // Clear status once text starts flowing
                  break;
                case "tool_call_start":
                  setToolCalls((prev) => [
                    ...prev,
                    {
                      tool_name: data.tool_name,
                      tool_input: data.tool_input,
                      status: "running",
                    },
                  ]);
                  break;
                case "tool_call_result":
                  setToolCalls((prev) =>
                    prev.map((tc) =>
                      tc.tool_name === data.tool_name && tc.status === "running"
                        ? { ...tc, status: data.success ? "completed" : "error" }
                        : tc
                    )
                  );
                  break;
                case "done":
                  setDoneData(data);
                  setIsStreaming(false);
                  break;
                case "error":
                  setError(data.message);
                  setIsStreaming(false);
                  break;
              }
            } catch {
              // Skip malformed JSON
            }
            currentEvent = "";
          } else if (line === "") {
            currentEvent = "";
          }
        }
      }
    } catch (err: any) {
      if (err.name === "AbortError" || err.message === "The user aborted a request.") {
        // User cancelled — not an error
        setIsStreaming(false);
        return;
      }
      setError(err.message || "Stream failed");
      setIsStreaming(false);
    } finally {
      abortControllerRef.current = null;
    }
  }, []);

  return {
    isStreaming,
    streamingText,
    statusMessage,
    toolCalls,
    doneData,
    error,
    sendMessage,
    cancel,
    reset,
  };
}
