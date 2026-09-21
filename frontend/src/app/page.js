/**
 * Main page — AI Dispensing Defect Detective chat interface.
 */

"use client";

import { useChat } from "@/hooks/useChat";
import ChatWindow from "@/components/ChatWindow";
import ChatInput from "@/components/ChatInput";
import KnowledgePackPanel from "@/components/KnowledgePackPanel";
import { useState } from "react";
import styles from "./page.module.css";

export default function Home() {
  const [activeView, setActiveView] = useState("diagnose");
  const { sessionId, messages, currentStep, isLoading, error, send } =
    useChat();

  return (
    <main className={styles.main} id="main-page">
      {/* Sidebar */}
      <aside className={styles.sidebar}>
        <div className={styles.logo}>
          <span className={styles.logoIcon}>DD</span>
          <h1 className={styles.logoText}>Defect Detective</h1>
        </div>
        <p className={styles.tagline}>
          AI-powered dispensing defect troubleshooter
        </p>

        <nav className={styles.nav} aria-label="Workspace">
          <button
            className={activeView === "diagnose" ? styles.navActive : styles.navButton}
            onClick={() => setActiveView("diagnose")}
            type="button"
          >
            Diagnose
          </button>
          <button
            className={activeView === "knowledge" ? styles.navActive : styles.navButton}
            onClick={() => setActiveView("knowledge")}
            type="button"
          >
            Knowledge
          </button>
        </nav>

        <div className={styles.sessionInfo}>
          <small>Session: {sessionId.slice(0, 8)}...</small>
        </div>
      </aside>

      {/* Chat area */}
      <div className={styles.workspace}>
        {activeView === "diagnose" ? (
          <div className={styles.chatArea}>
            <ChatWindow
              messages={messages}
              isLoading={isLoading}
              currentStep={currentStep}
            />

            {error && <div className={styles.error}>{error}</div>}

            <ChatInput onSend={send} isLoading={isLoading} />
          </div>
        ) : (
          <KnowledgePackPanel />
        )}
      </div>
    </main>
  );
}
