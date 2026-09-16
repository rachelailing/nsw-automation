/**
 * ChatInput component — text input + send button for the chat.
 */

"use client";

import { useState } from "react";
import styles from "./ChatInput.module.css";

export default function ChatInput({ onSend, isLoading }) {
  const [text, setText] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!text.trim() || isLoading) return;
    onSend(text.trim());
    setText("");
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <textarea
        className={styles.input}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Describe your dispensing problem..."
        rows={1}
        disabled={isLoading}
        id="chat-input"
      />
      <button
        className={styles.sendBtn}
        type="submit"
        disabled={!text.trim() || isLoading}
        id="send-button"
      >
        Send
      </button>
    </form>
  );
}
