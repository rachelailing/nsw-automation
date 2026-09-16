/**
 * Main page — AI Dispensing Defect Detective chat interface.
 */

"use client";

import { useChat } from "@/hooks/useChat";
import ChatWindow from "@/components/ChatWindow";
import ChatInput from "@/components/ChatInput";
import ImageUpload from "@/components/ImageUpload";
import styles from "./page.module.css";

export default function Home() {
  const { sessionId, messages, currentStep, isLoading, error, send } =
    useChat();

  return (
    <main className={styles.main} id="main-page">
      {/* Sidebar */}
      <aside className={styles.sidebar}>
        <div className={styles.logo}>
          <span className={styles.logoIcon}>🔍</span>
          <h1 className={styles.logoText}>Defect Detective</h1>
        </div>
        <p className={styles.tagline}>
          AI-powered dispensing defect troubleshooter
        </p>

        <ImageUpload sessionId={sessionId} />

        <div className={styles.sessionInfo}>
          <small>Session: {sessionId.slice(0, 8)}...</small>
        </div>
      </aside>

      {/* Chat area */}
      <div className={styles.chatArea}>
        <ChatWindow
          messages={messages}
          isLoading={isLoading}
          currentStep={currentStep}
        />

        {error && <div className={styles.error}>⚠️ {error}</div>}

        <ChatInput onSend={send} isLoading={isLoading} />
      </div>
    </main>
  );
}
