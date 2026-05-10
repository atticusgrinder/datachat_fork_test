import { useState, useRef, useCallback } from "react";
import { api, VisualizationConfig } from "@/lib/api";

export interface ToolCallInfo {
  tool_name: string;
  tool_input?: Record<string, any>;
  status: "running" | "completed" | "error";
}

export interface DemoStreamDoneData {
  conversation_id: string;
  response_text: string;
  tokens_remaining: number;
  messages_remaining: number;
  visualization: VisualizationConfig | null;
  chart_data: Record<string, any>[] | null;
  duration_ms: number;
  input_tokens: number;
  output_tokens: number;
}

interface UseDemoStreamingReturn {
  isStreaming: boolean;
  streamingText: string;
  statusMessage: string;
  toolCalls: ToolCallInfo[];
  doneData: DemoStreamDoneData | null;
  error: string | null;
  sendMessage: (params: {
    message: string;
    session_id: string;
    conversation_id?: string;
  }) => Promise<void>;
  cancel: () => void;
  reset: () => void;
}

export function useDemoStreaming(): UseDemoStreamingReturn {
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [statusMessage, setStatusMessage] = useState("");
  const [toolCalls, setToolCalls] = useState<ToolCallInfo[]>([]);
  const [doneData, setDoneData] = useState<DemoStreamDoneData | null>(null);
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
    session_id: string;
    conversation_id?: string;
  }) => {
    setIsStreaming(true);
    setStreamingText("");
    setStatusMessage("");
    setToolCalls([]);
    setDoneData(null);
    setError(null);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const response = await api.sendDemoMessageStream({
        ...params,
        signal: controller.signal,
      });

      const reader = response.body?.getReader();
      if (!reader) throw new Error("No response body");

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

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
                  setStatusMessage("");
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
