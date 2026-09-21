/**
 * useChat hook — manages the chat conversation state.
 *
 * Handles sending messages, receiving responses, tracking the current
 * step in the troubleshooting flow, and managing loading states.
 */

"use client";

import { useState, useCallback } from "react";
import { sendMessage } from "@/lib/api";
import { v4 as uuidv4 } from "uuid";

export function useChat() {
  const [sessionId] = useState(() => {
    if (typeof window === "undefined") return uuidv4();

    const existingSessionId = window.localStorage.getItem("defectDetectiveSessionId");
    if (existingSessionId) return existingSessionId;

    const newSessionId = uuidv4();
    window.localStorage.setItem("defectDetectiveSessionId", newSessionId);
    return newSessionId;
  });
  const [messages, setMessages] = useState([]);
  const [currentStep, setCurrentStep] = useState("questioning");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const send = useCallback(
    async (text) => {
      if (!text.trim() || isLoading) return;

      // Add user message
      const userMessage = { role: "user", content: text, timestamp: Date.now() };
      setMessages((prev) => [...prev, userMessage]);
      setIsLoading(true);
      setError(null);

      try {
        const response = await sendMessage(sessionId, text);

        // Add AI response
        const aiMessage = {
          role: "assistant",
          content: response.reply,
          timestamp: Date.now(),
        };
        setMessages((prev) => [...prev, aiMessage]);
        setCurrentStep(response.step);
      } catch (err) {
        setError(err.message);
        console.error("Chat error:", err);
      } finally {
        setIsLoading(false);
      }
    },
    [sessionId, isLoading]
  );

  return {
    sessionId,
    messages,
    currentStep,
    isLoading,
    error,
    send,
  };
}
